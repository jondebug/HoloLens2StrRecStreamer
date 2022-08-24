//*********************************************************
//
// Copyright (c) Microsoft. All rights reserved.
// This code is licensed under the MIT License (MIT).
// THIS CODE IS PROVIDED *AS IS* WITHOUT WARRANTY OF
// ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING ANY
// IMPLIED WARRANTIES OF FITNESS FOR A PARTICULAR
// PURPOSE, MERCHANTABILITY, OR NON-INFRINGEMENT.
//
//*********************************************************

#include "RMCameraReader.h"
#include <winrt/Windows.Networking.Sockets.h>
#include <winrt/Windows.Storage.Streams.h>

#include <sstream>
#define DBG_ENABLE_ERROR_LOGGING 1
#define DBG_ENABLE_VERBOSE_LOGGING 1

using namespace winrt::Windows::Networking::Sockets;
using namespace winrt::Windows::Storage::Streams;
using namespace winrt::Windows::Perception;
using namespace winrt::Windows::Perception::Spatial;
using namespace winrt::Windows::Foundation::Numerics;
using namespace winrt::Windows::Storage;


namespace Depth
{
    enum InvalidationMasks
    {
        Invalid = 0x80,
    };
    static constexpr UINT16 AHAT_INVALID_VALUE = 4090;
}
bool RMCameraReader::getWriterState()
{
    if (m_writer)
    {
        return true;
    }
    return false;
}
void RMCameraReader::CameraUpdateThread(RMCameraReader* pCameraReader, HANDLE camConsentGiven, ResearchModeSensorConsent* camAccessConsent)
{
	HRESULT hr = S_OK;

    DWORD waitResult = WaitForSingleObject(camConsentGiven, INFINITE);

    if (waitResult == WAIT_OBJECT_0)
    {
        switch (*camAccessConsent)
        {
        case ResearchModeSensorConsent::Allowed:
            OutputDebugString(L"Access is granted");
            break;
        case ResearchModeSensorConsent::DeniedBySystem:
            OutputDebugString(L"Access is denied by the system");
            hr = E_ACCESSDENIED;
            break;
        case ResearchModeSensorConsent::DeniedByUser:
            OutputDebugString(L"Access is denied by the user");
            hr = E_ACCESSDENIED;
            break;
        case ResearchModeSensorConsent::NotDeclaredByApp:
            OutputDebugString(L"Capability is not declared in the app manifest");
            hr = E_ACCESSDENIED;
            break;
        case ResearchModeSensorConsent::UserPromptRequired:
            OutputDebugString(L"Capability user prompt required");
            hr = E_ACCESSDENIED;
            break;
        default:
            OutputDebugString(L"Access is denied by the system");
            hr = E_ACCESSDENIED;
            break;
        }
    }
    else
    {
        hr = E_UNEXPECTED;
    }

    if (SUCCEEDED(hr))
    {
        hr = pCameraReader->m_pRMSensor->OpenStream();

        if (FAILED(hr))
        {
            pCameraReader->m_pRMSensor->Release();
            pCameraReader->m_pRMSensor = nullptr;
        }

        while (!pCameraReader->m_fExit && pCameraReader->m_pRMSensor)
        {
            HRESULT hr = S_OK;
            IResearchModeSensorFrame* pSensorFrame = nullptr;

            hr = pCameraReader->m_pRMSensor->GetNextBuffer(&pSensorFrame);

            if (SUCCEEDED(hr))
            {
                std::lock_guard<std::mutex> guard(pCameraReader->m_sensorFrameMutex);
                if (pCameraReader->m_pSensorFrame)
                {
                    pCameraReader->m_pSensorFrame->Release();
                }
                pCameraReader->m_pSensorFrame = pSensorFrame;
            }
        }

        if (pCameraReader->m_pRMSensor)
        {
            pCameraReader->m_pRMSensor->CloseStream();
        }
    }
}

void RMCameraReader::CameraWriteThread(RMCameraReader* pReader)
{
    while (!pReader->m_fExit)
    {
        std::unique_lock<std::mutex> storage_lock(pReader->m_storageMutex);
        if (pReader->m_storageFolder == nullptr)
        {
            pReader->m_storageCondVar.wait(storage_lock);
        }
        
        std::lock_guard<std::mutex> reader_guard(pReader->m_sensorFrameMutex);
        if (pReader->m_pSensorFrame)
        {
            if (pReader->IsNewTimestamp(pReader->m_pSensorFrame))
            {
                pReader->SaveFrame(pReader->m_pSensorFrame);
            }
        }       
    }	
}

void RMCameraReader::CameraSendThread(RMCameraReader* pReader)
{
#if DBG_ENABLE_INFO_LOGGING
    OutputDebugString(L"detphStreamer::CameraStreamThread: Starting processing thread.\n");
#endif
    while (!pReader->m_fExit)
    {
        std::lock_guard<std::mutex> reader_guard(pReader->m_sensorFrameMutex);
        if (pReader->m_pSensorFrame && pReader->m_writer)
        {
            if (pReader->IsNewTimestamp(pReader->m_pSensorFrame))
            {
                if (pReader->m_isExtrinsicsSent)
                {
                    pReader->SaveFrame(pReader->m_pSensorFrame);
                    pReader->m_writeInProgress = false;
                }
                else
                {
                    pReader->m_isExtrinsicsSent = true;
                    pReader->DumpCalibration();
                    pReader->m_writeInProgress = false;
                }
            }
        }
    }
}
// sends the LUT. need to be send first.
void RMCameraReader::DumpCalibration()
{   
    // Get frame resolution (could also be stored once at the beginning of the capture)
    ResearchModeSensorResolution resolution;
    {
        //std::lock_guard<std::mutex> guard(this->m_sensorFrameMutex);
        // Assuming we are at the end of the capture
        assert(m_pSensorFrame != nullptr);
        winrt::check_hresult(m_pSensorFrame->GetResolution(&resolution)); 
    }

    // Get camera sensor object
    IResearchModeCameraSensor* pCameraSensor = nullptr;    
    HRESULT hr = m_pRMSensor->QueryInterface(IID_PPV_ARGS(&pCameraSensor));
    winrt::check_hresult(hr);

    // Get extrinsics (rotation and translation) with respect to the rigNode
    DirectX::XMFLOAT4X4 cameraViewMatrix;

    pCameraSensor->GetCameraExtrinsicsMatrix(&cameraViewMatrix);

    const float4x4 sensorExtrinsics(
        cameraViewMatrix.m[0][0], cameraViewMatrix.m[1][0], cameraViewMatrix.m[2][0], cameraViewMatrix.m[3][0],
        cameraViewMatrix.m[0][1], cameraViewMatrix.m[1][1], cameraViewMatrix.m[2][1], cameraViewMatrix.m[3][1],
        cameraViewMatrix.m[0][2], cameraViewMatrix.m[1][2], cameraViewMatrix.m[2][2], cameraViewMatrix.m[3][2],
        cameraViewMatrix.m[0][3], cameraViewMatrix.m[1][3], cameraViewMatrix.m[2][3], cameraViewMatrix.m[3][3]);

    // LUT     
    float uv[2];
    float xy[2];
    std::vector<float> lutTable(size_t(resolution.Width * resolution.Height) * 3);
    auto pLutTable = lutTable.data();

    for (size_t y = 0; y < resolution.Height; y++)
    {
        uv[1] = (y + 0.5f);
        for (size_t x = 0; x < resolution.Width; x++)
        {
            uv[0] = (x + 0.5f);
            hr = pCameraSensor->MapImagePointToCameraUnitPlane(uv, xy);
            if (FAILED(hr))
            {
				*pLutTable++ = xy[0];
				*pLutTable++ = xy[1];
				*pLutTable++ = 0.f;
                continue;
            }
            float z = 1.0f;
            const float norm = sqrtf(xy[0] * xy[0] + xy[1] * xy[1] + z * z);
            const float invNorm = 1.0f / norm;
            xy[0] *= invNorm;
            xy[1] *= invNorm;
            z *= invNorm;

            // Dump LUT row
            *pLutTable++ = xy[0];
            *pLutTable++ = xy[1];
            *pLutTable++ = z;
        }
    }    
    pCameraSensor->Release();

    // LUT 
    const unsigned char* lutToBytes = reinterpret_cast<const unsigned char*> (lutTable.data());
    std::vector<unsigned char> lutTableByteData(lutToBytes, lutToBytes + sizeof(float) * lutTable.size());
    m_lutTableByteData = lutTableByteData;

    if (m_writeInProgress)
    {
#if DBG_ENABLE_VERBOSE_LOGGING
        OutputDebugStringW(L"Streamer::SendExtrinsics: Write already in progress.\n");
#endif
        return;
    }
    m_writeInProgress = true;

    try
    {
        // Write header
        WriteMatrix4x4(sensorExtrinsics);
        m_writer.WriteBytes(lutTableByteData);

#if DBG_ENABLE_VERBOSE_LOGGING
        OutputDebugStringW(L"Streamer::SendExtrinsics: Trying to store writer...\n");
#endif
        m_writer.StoreAsync();
    }
    catch (winrt::hresult_error const& ex)
    {
        SocketErrorStatus webErrorStatus{ SocketError::GetStatus(ex.to_abi()) };
        if (webErrorStatus == SocketErrorStatus::ConnectionResetByPeer)
        {
            // the client disconnected!
            m_writer == nullptr;
            m_streamSocket == nullptr;
            m_writeInProgress = false;
        }
#if DBG_ENABLE_ERROR_LOGGING
        winrt::hstring message = ex.message();
        OutputDebugStringW(L"Streamer::SendExtrinsics: Sending failed with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
#endif // DBG_ENABLE_ERROR_LOGGING
    }

    m_writeInProgress = false;

#if DBG_ENABLE_VERBOSE_LOGGING
    OutputDebugStringW(L"Streamer::SendExtrinsics: Extrinsics sent!\n");
#endif

    return;
}

//void RMCameraReader::DumpFrameLocations()
//{
//    for (const FrameLocation& location : m_frameLocations)
//    {
//        file << location.timestamp << "," <<
//            location.rigToWorldtransform.m11 << "," << location.rigToWorldtransform.m21 << "," << location.rigToWorldtransform.m31 << "," << location.rigToWorldtransform.m41 << "," <<
//            location.rigToWorldtransform.m12 << "," << location.rigToWorldtransform.m22 << "," << location.rigToWorldtransform.m32 << "," << location.rigToWorldtransform.m42 << "," <<
//            location.rigToWorldtransform.m13 << "," << location.rigToWorldtransform.m23 << "," << location.rigToWorldtransform.m33 << "," << location.rigToWorldtransform.m43 << "," <<
//            location.rigToWorldtransform.m14 << "," << location.rigToWorldtransform.m24 << "," << location.rigToWorldtransform.m34 << "," << location.rigToWorldtransform.m44 << std::endl;
//    }
//    file.close();
//
//    m_frameLocations.clear();
//}

void RMCameraReader::SetLocator(const GUID& guid)
{
    m_locator = Preview::SpatialGraphInteropPreview::CreateLocatorForNode(guid);
}

bool RMCameraReader::IsNewTimestamp(IResearchModeSensorFrame* pSensorFrame)
{
    ResearchModeSensorTimestamp timestamp;
    winrt::check_hresult(pSensorFrame->GetTimeStamp(&timestamp));

    if (m_prevTimestamp == timestamp.HostTicks)
    {
        return false;
    }

    m_prevTimestamp = timestamp.HostTicks;

    return true;
}

void RMCameraReader::SetStorageFolder(const StorageFolder& storageFolder)
{
    std::lock_guard<std::mutex> storage_guard(m_storageMutex);
    m_storageFolder = storageFolder;
    wchar_t fileName[MAX_PATH] = {};    
    swprintf_s(fileName, L"%s\\%s.tar", m_storageFolder.Path().data(), m_pRMSensor->GetFriendlyName());
    m_tarball.reset(new Io::Tarball(fileName));
    m_storageCondVar.notify_all();
}

void RMCameraReader::ResetStorageFolder()
{
    std::lock_guard<std::mutex> storage_guard(m_storageMutex);
    DumpCalibration();
    //DumpFrameLocations();
    m_tarball.reset();
    m_storageFolder = nullptr;
}

void RMCameraReader::SetWorldCoordSystem(const SpatialCoordinateSystem& coordSystem)
{
    m_worldCoordSystem = coordSystem;
}

std::string CreateHeader(const ResearchModeSensorResolution& resolution, int maxBitmapValue)
{
    std::string bitmapFormat = "P5"; 

    // Compose PGM header string
    std::stringstream header;
    header << bitmapFormat << "\n"
        << resolution.Width << " "
        << resolution.Height << "\n"
        << maxBitmapValue << "\n";
    return header.str();
}

void RMCameraReader::SaveDepth(IResearchModeSensorFrame* pSensorFrame, IResearchModeSensorDepthFrame* pDepthFrame)
{        
    // get rig2world
    auto timestamp = PerceptionTimestampHelper::FromSystemRelativeTargetTime(HundredsOfNanoseconds(checkAndConvertUnsigned(m_prevTimestamp)));
    auto location = m_locator.TryLocateAtTimestamp(timestamp, m_worldCoordSystem);
    if (!location) //TODO: maybe delete the return
    {
        return;
    }
    const float4x4 rig2worldTransform = make_float4x4_from_quaternion(location.Orientation()) * make_float4x4_translation(location.Position());
    auto absoluteTimestamp = m_converter.RelativeTicksToAbsoluteTicks(HundredsOfNanoseconds((long long)m_prevTimestamp)).count();

    // Get resolution (will be used for PGM header)
    ResearchModeSensorResolution resolution;    
    pSensorFrame->GetResolution(&resolution);  

    int imageWidth = resolution.Width;
    int imageHeight = resolution.Height;
    int pixelStride = resolution.BytesPerPixel;
    int rowStride = imageWidth * pixelStride;

    bool isLongThrow = (m_pRMSensor->GetSensorType() == DEPTH_LONG_THROW);

    const UINT16* pAbImage = nullptr;
    size_t outAbBufferCount = 0;
    //wchar_t outputAbPath[MAX_PATH];

    const UINT16* pDepth = nullptr;
    size_t outDepthBufferCount = 0;
    //wchar_t outputDepthPath[MAX_PATH];

    const BYTE* pSigma = nullptr;
    size_t outSigmaBufferCount = 0;

    if (isLongThrow)
    {
        winrt::check_hresult(pDepthFrame->GetSigmaBuffer(&pSigma, &outSigmaBufferCount));
    }

    winrt::check_hresult(pDepthFrame->GetAbDepthBuffer(&pAbImage, &outAbBufferCount));
    winrt::check_hresult(pDepthFrame->GetBuffer(&pDepth, &outDepthBufferCount));

    // Get header for AB and Depth (16 bits)
    // Prepare the data to save for AB
    //const std::string abHeaderString = CreateHeader(resolution, 65535);
    //swprintf_s(outputAbPath, L"%llu_ab.pgm", timestamp.count());
    //std::vector<BYTE> abPgmData;
    //abPgmData.reserve(abHeaderString.size() + outAbBufferCount * sizeof(UINT16));
    //abPgmData.insert(abPgmData.end(), abHeaderString.c_str(), abHeaderString.c_str() + abHeaderString.size());
    
    // Prepare the data to save for Depth
    //const std::string depthHeaderString = CreateHeader(resolution, 65535);
    //swprintf_s(outputDepthPath, L"%llu.pgm", timestamp.count());
    std::vector<BYTE> sensorByteData;
    sensorByteData.reserve(outDepthBufferCount * sizeof(UINT16));
   // sensorByteData.insert(sensorByteData.end(), depthHeaderString.c_str(), depthHeaderString.c_str() + depthHeaderString.size());
    
    assert(outAbBufferCount == outDepthBufferCount);
    if (isLongThrow)
        assert(outAbBufferCount == outSigmaBufferCount);
    // Validate depth
    for (size_t i = 0; i < outAbBufferCount; ++i)
    {
        UINT16 d;
        const bool invalid = isLongThrow ? ((pSigma[i] & Depth::InvalidationMasks::Invalid) > 0) :
                                           (pDepth[i] >= Depth::AHAT_INVALID_VALUE);
        if (invalid)
        {
            d = 0;
        }
        else
        {            
            d = pDepth[i];
        }

        sensorByteData.push_back((BYTE)d);
        sensorByteData.push_back((BYTE)(d >> 8));
    }

//   m_tarball->AddFile(outputAbPath, &abPgmData[0], abPgmData.size());
//    m_tarball->AddFile(outputDepthPath, &depthPgmData[0], depthPgmData.size());

    // stream the frame

    if (m_writeInProgress)
    {
#if DBG_ENABLE_VERBOSE_LOGGING
        OutputDebugStringW(L"Streamer::SendFrame: Write already in progress.\n");
#endif
        return;
    }

    m_writeInProgress = true;

    try
    {
        // Write header
        m_writer.WriteUInt64(absoluteTimestamp);
        m_writer.WriteInt32(imageWidth);
        m_writer.WriteInt32(imageHeight);
        m_writer.WriteInt32(pixelStride);
        m_writer.WriteInt32(rowStride);

        WriteMatrix4x4(rig2worldTransform);

        m_writer.WriteBytes(sensorByteData);

#if DBG_ENABLE_VERBOSE_LOGGING
        OutputDebugStringW(L"Streamer::SendFrame: Trying to store writer...\n");
#endif
        m_writer.StoreAsync();
    }
    catch (winrt::hresult_error const& ex)
    {
        SocketErrorStatus webErrorStatus{ SocketError::GetStatus(ex.to_abi()) };
        if (webErrorStatus == SocketErrorStatus::ConnectionResetByPeer)
        {
            // the client disconnected!
            m_writer == nullptr;
            m_streamSocket == nullptr;
            m_writeInProgress = false;
        }
#if DBG_ENABLE_ERROR_LOGGING
        winrt::hstring message = ex.message();
        OutputDebugStringW(L"Streamer::SendFrame: Sending failed with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
#endif // DBG_ENABLE_ERROR_LOGGING
    }

    m_writeInProgress = false;

#if DBG_ENABLE_VERBOSE_LOGGING
    OutputDebugStringW(L"Streamer::SendFrame: Frame sent!\n");
#endif
}

void RMCameraReader::SaveVLC(IResearchModeSensorFrame* pSensorFrame, IResearchModeSensorVLCFrame* pVLCFrame)
{        
    wchar_t outputPath[MAX_PATH];

    // Get PGM header
    int maxBitmapValue = 255;
    ResearchModeSensorResolution resolution;
    winrt::check_hresult(pSensorFrame->GetResolution(&resolution));

    const std::string headerString = CreateHeader(resolution, maxBitmapValue);

    // Compose the output file name using absolute ticks
    swprintf_s(outputPath, L"%llu.pgm", m_converter.RelativeTicksToAbsoluteTicks(HundredsOfNanoseconds(checkAndConvertUnsigned(m_prevTimestamp))).count());

    // Convert the software bitmap to raw bytes    
    std::vector<BYTE> pgmData;
    size_t outBufferCount = 0;
    const BYTE* pImage = nullptr;

    winrt::check_hresult(pVLCFrame->GetBuffer(&pImage, &outBufferCount));

    pgmData.reserve(headerString.size() + outBufferCount);
    pgmData.insert(pgmData.end(), headerString.c_str(), headerString.c_str() + headerString.size());
    pgmData.insert(pgmData.end(), pImage, pImage + outBufferCount);

    m_tarball->AddFile(outputPath, &pgmData[0], pgmData.size());
}

void RMCameraReader::SaveFrame(IResearchModeSensorFrame* pSensorFrame)
{
	IResearchModeSensorVLCFrame* pVLCFrame = nullptr;
	IResearchModeSensorDepthFrame* pDepthFrame = nullptr;

    HRESULT hr = pSensorFrame->QueryInterface(IID_PPV_ARGS(&pVLCFrame));

	if (FAILED(hr))
	{
		hr = pSensorFrame->QueryInterface(IID_PPV_ARGS(&pDepthFrame));
	}

	if (pVLCFrame)
	{
		SaveVLC(pSensorFrame, pVLCFrame);
        pVLCFrame->Release();
	}

	if (pDepthFrame)
	{		
		SaveDepth(pSensorFrame, pDepthFrame);
        pDepthFrame->Release();
	}    
}

bool RMCameraReader::AddFrameLocation()
{         
    auto timestamp = PerceptionTimestampHelper::FromSystemRelativeTargetTime(HundredsOfNanoseconds(checkAndConvertUnsigned(m_prevTimestamp)));
    auto location = m_locator.TryLocateAtTimestamp(timestamp, m_worldCoordSystem);
    if (!location)
    {
        return false;
    }
    const float4x4 dynamicNodeToCoordinateSystem = make_float4x4_from_quaternion(location.Orientation()) * make_float4x4_translation(location.Position());
    auto absoluteTimestamp = m_converter.RelativeTicksToAbsoluteTicks(HundredsOfNanoseconds((long long)m_prevTimestamp)).count();
    //m_frameLocations.push_back(std::move(FrameLocation{absoluteTimestamp, dynamicNodeToCoordinateSystem}));


    return true;
}


void RMCameraReader::WriteMatrix4x4(
    _In_ winrt::Windows::Foundation::Numerics::float4x4 matrix)
{
    m_writer.WriteSingle(matrix.m11);
    m_writer.WriteSingle(matrix.m12);
    m_writer.WriteSingle(matrix.m13);
    m_writer.WriteSingle(matrix.m14);

    m_writer.WriteSingle(matrix.m21);
    m_writer.WriteSingle(matrix.m22);
    m_writer.WriteSingle(matrix.m23);
    m_writer.WriteSingle(matrix.m24);

    m_writer.WriteSingle(matrix.m31);
    m_writer.WriteSingle(matrix.m32);
    m_writer.WriteSingle(matrix.m33);
    m_writer.WriteSingle(matrix.m34);

    m_writer.WriteSingle(matrix.m41);
    m_writer.WriteSingle(matrix.m42);
    m_writer.WriteSingle(matrix.m43);
    m_writer.WriteSingle(matrix.m44);
}
//winrt::Windows::Foundation::IAsyncAction
void RMCameraReader::InitializeAsync(
    const long long minDelta,
    const winrt::Windows::Perception::Spatial::SpatialCoordinateSystem& coordSystem,
    std::wstring portName)
{
    OutputDebugStringW(L"depthStreamer::InitializeAsync: Creating depth frame Streamer\n");

    m_worldCoordSystem = coordSystem;
    m_portName = portName;
    m_minDelta = minDelta;

    StartServer();


}


winrt::Windows::Foundation::IAsyncAction RMCameraReader::StartServer()
{
    try
    {
        // The ConnectionReceived event is raised when connections are received.
        m_streamSocketListener.ConnectionReceived({ this, &RMCameraReader::OnConnectionReceived });

        // Start listening for incoming TCP connections on the specified port. You can specify any port that's not currently in use.
        // Every protocol typically has a standard port number. For example, HTTP is typically 80, FTP is 20 and 21, etc.
        // For this example, we'll choose an arbitrary port number.
        co_await m_streamSocketListener.BindServiceNameAsync(m_portName);
        //m_streamSocketListener.Control().KeepAlive(true);

        wchar_t msgBuffer[200];
        swprintf_s(msgBuffer, L"depthStreamer::StartServer: Server is listening at %ls \n",
            m_portName.c_str());
        OutputDebugStringW(msgBuffer);
    }
    catch (winrt::hresult_error const& ex)
    {
        SocketErrorStatus webErrorStatus{ SocketError::GetStatus(ex.to_abi()) };
        winrt::hstring message = webErrorStatus != SocketErrorStatus::Unknown ?
            winrt::to_hstring((int32_t)webErrorStatus) : winrt::to_hstring(ex.to_abi());
        OutputDebugStringW(L"depthStreamer::StartServer:: Failed to open listener with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
    }
}

void RMCameraReader::OnConnectionReceived(
    winrt::Windows::Networking::Sockets::StreamSocketListener sender,
    winrt::Windows::Networking::Sockets::StreamSocketListenerConnectionReceivedEventArgs args)
{
    try
    {
        m_streamSocket = args.Socket();
        m_writer = (winrt::Windows::Storage::Streams::DataWriter)args.Socket().OutputStream();
        m_writer.UnicodeEncoding(UnicodeEncoding::Utf8);
        m_writer.ByteOrder(ByteOrder::LittleEndian);

        m_writeInProgress = false;
        m_pStreamThread = new std::thread(CameraSendThread, this);
#if DBG_ENABLE_INFO_LOGGING
        OutputDebugStringW(L"depthStreamer::OnConnectionReceived: Received connection! \n");

#endif
    }
    catch (winrt::hresult_error const& ex)
    {
#if DBG_ENABLE_ERROR_LOGGING
        SocketErrorStatus webErrorStatus{ SocketError::GetStatus(ex.to_abi()) };
        winrt::hstring message = webErrorStatus != SocketErrorStatus::Unknown ?
            winrt::to_hstring((int32_t)webErrorStatus) : winrt::to_hstring(ex.to_abi());
        OutputDebugStringW(L"depthStreamer::StartServer: Failed to open listener with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
#endif
    }
}
