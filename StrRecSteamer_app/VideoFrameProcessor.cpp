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

#include "VideoFrameProcessor.h"
#include <winrt/Windows.Foundation.Collections.h>
#include <fstream>

#define DBG_ENABLE_ERROR_LOGGING 1
#define DBG_ENABLE_VERBOSE_LOGGING 1

using namespace winrt::Windows::Foundation::Collections;
using namespace winrt::Windows::Media::Capture;
using namespace winrt::Windows::Media::Capture::Frames;
using namespace winrt::Windows::Perception::Spatial;
using namespace winrt::Windows::Graphics::Imaging;
using namespace winrt::Windows::Networking::Sockets;
using namespace winrt::Windows::Storage::Streams;
using namespace winrt::Windows::Storage;
const int VideoFrameProcessor::kImageWidth = 960;
const wchar_t VideoFrameProcessor::kSensorName[3] = L"PV";

winrt::Windows::Foundation::IAsyncAction VideoFrameProcessor::InitializeAsync(const long long minDelta,
    const winrt::Windows::Perception::Spatial::SpatialCoordinateSystem& coordSystem,
    std::wstring pv_portName)
{
     m_worldCoordSystem = coordSystem;
     m_pv_portName = pv_portName;
     m_minDelta = minDelta;
     m_streamingEnabled = true;

    auto mediaFrameSourceGroups{ co_await MediaFrameSourceGroup::FindAllAsync() };

    MediaFrameSourceGroup selectedSourceGroup = nullptr;
    MediaCaptureVideoProfile profile = nullptr;
    MediaCaptureVideoProfileMediaDescription desc = nullptr;
    std::vector<MediaFrameSourceInfo> selectedSourceInfos;

    // Find MediaFrameSourceGroup
    for (const MediaFrameSourceGroup& mediaFrameSourceGroup : mediaFrameSourceGroups)
    {
        auto knownProfiles = MediaCapture::FindKnownVideoProfiles(mediaFrameSourceGroup.Id(), KnownVideoProfile::VideoConferencing);
        for (const auto& knownProfile : knownProfiles)
        {
            for (auto knownDesc : knownProfile.SupportedRecordMediaDescription())
            {
                if ((knownDesc.Width() == kImageWidth)) // && (std::round(knownDesc.FrameRate()) == 15))
                {
                    profile = knownProfile;
                    desc = knownDesc;
                    selectedSourceGroup = mediaFrameSourceGroup;
                    break;
                }
            }
        }
    }

    winrt::check_bool(selectedSourceGroup != nullptr);

    for (auto sourceInfo : selectedSourceGroup.SourceInfos())
    {
        // Workaround since multiple Color sources can be found,
        // and not all of them are necessarily compatible with the selected video profile
        if (sourceInfo.SourceKind() == MediaFrameSourceKind::Color)
        {
            selectedSourceInfos.push_back(sourceInfo);
        }
    }
    winrt::check_bool(!selectedSourceInfos.empty());
    
    // Initialize a MediaCapture object
    MediaCaptureInitializationSettings settings;
    settings.VideoProfile(profile);
    settings.RecordMediaDescription(desc);
    settings.VideoDeviceId(selectedSourceGroup.Id());
    settings.StreamingCaptureMode(StreamingCaptureMode::Video);
    settings.MemoryPreference(MediaCaptureMemoryPreference::Cpu);
    settings.SharingMode(MediaCaptureSharingMode::ExclusiveControl);
    settings.SourceGroup(selectedSourceGroup);

    MediaCapture mediaCapture = MediaCapture();
    co_await mediaCapture.InitializeAsync(settings);

    MediaFrameSource selectedSource = nullptr;
    MediaFrameFormat preferredFormat = nullptr;

    for (MediaFrameSourceInfo sourceInfo : selectedSourceInfos)
    {
        auto tmpSource = mediaCapture.FrameSources().Lookup(sourceInfo.Id());
        for (MediaFrameFormat format : tmpSource.SupportedFormats())
        {
            if (format.VideoFormat().Width() == kImageWidth)
            {
                selectedSource = tmpSource;
                preferredFormat = format;
                break;
            }
        }
    }

    winrt::check_bool(preferredFormat != nullptr);

    co_await selectedSource.SetFormatAsync(preferredFormat);
    auto mediaFrameReader = co_await mediaCapture.CreateFrameReaderAsync(selectedSource);
    auto status = co_await mediaFrameReader.StartAsync();

    winrt::check_bool(status == MediaFrameReaderStartStatus::Success);

    StartPvServer();
    m_pStreamThread = new std::thread(CameraStreamThread, this);

    // TODO: do we need 300 frames as a buffer?
    // 
    //// reserve for 10 seconds at 30fps
    //m_PVFrameLog.reserve(10 * 30);
    //m_pWriteThread = new std::thread(CameraWriteThread, this);

    m_OnFrameArrivedRegistration = mediaFrameReader.FrameArrived({ this, &VideoFrameProcessor::OnFrameArrived });
    OutputDebugStringW(L"VideoCameraStreamer::InitializeAsync: Done. \n");
}


winrt::Windows::Foundation::IAsyncAction VideoFrameProcessor::StartPvServer()
{
    try
    {
        // The ConnectionReceived event is raised when connections are received.
        m_StreamSocketListener.ConnectionReceived({ this, &VideoFrameProcessor::OnPvConnectionReceived });

        // Start listening for incoming TCP connections on the specified port. You can specify any port that's not currently in use.
        // Every protocol typically has a standard port number. For example, HTTP is typically 80, FTP is 20 and 21, etc.
        // For this example, we'll choose an arbitrary port number.
        co_await m_StreamSocketListener.BindServiceNameAsync(m_pv_portName);
        //m_streamSocketListener.Control().KeepAlive(true);
   
        wchar_t msgBuffer[200];
        swprintf_s(msgBuffer, L"VideoCameraStreamer::StartServer: Server is listening at %ls \n",
            m_pv_portName.c_str());
        OutputDebugStringW(msgBuffer);
    }
    catch (winrt::hresult_error const& ex)
    {
        SocketErrorStatus webErrorStatus{ SocketError::GetStatus(ex.to_abi()) };
        winrt::hstring message = webErrorStatus != SocketErrorStatus::Unknown ?
            winrt::to_hstring((int32_t)webErrorStatus) : winrt::to_hstring(ex.to_abi());
        OutputDebugStringW(L"VideoCameraStreamer::StartServer: Failed to open listener with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
    }
}

void VideoFrameProcessor::OnPvConnectionReceived(
    winrt::Windows::Networking::Sockets::StreamSocketListener sender,
    winrt::Windows::Networking::Sockets::StreamSocketListenerConnectionReceivedEventArgs args)
{
    try
    {
        m_StreamSocket = args.Socket();
        m_writer = (winrt::Windows::Storage::Streams::DataWriter)args.Socket().OutputStream();
        m_writer.UnicodeEncoding(UnicodeEncoding::Utf8);
        m_writer.ByteOrder(ByteOrder::LittleEndian);

        m_writeInProgress = false;
#if DBG_ENABLE_INFO_LOGGING
        OutputDebugStringW(L"VideoCameraStreamer::OnConnectionReceived: Received connection! \n");
#endif
    }
    catch (winrt::hresult_error const& ex)
    {
#if DBG_ENABLE_ERROR_LOGGING
        SocketErrorStatus webErrorStatus{ SocketError::GetStatus(ex.to_abi()) };
        winrt::hstring message = webErrorStatus != SocketErrorStatus::Unknown ?
            winrt::to_hstring((int32_t)webErrorStatus) : winrt::to_hstring(ex.to_abi());
        OutputDebugStringW(L"VideoCameraStreamer::StartServer: Failed to open listener with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
#endif
    }
}

void VideoFrameProcessor::CameraStreamThread(VideoFrameProcessor* pStreamer)
{
#if DBG_ENABLE_INFO_LOGGING
    OutputDebugString(L"VideoCameraStreamer::CameraStreamThread: Starting streaming thread.\n");
#endif
    while (!pStreamer->m_fExit)
    {
        //std::lock_guard<std::shared_mutex> reader_guard(pStreamer->m_EyeGazeframeMutex);
        std::lock_guard<std::shared_mutex> reader_guard(pStreamer->m_frameMutex);
        if (pStreamer->m_latestFrame)
        {
            auto frame = pStreamer->m_latestFrame;
            long long timestamp = pStreamer->m_converter.RelativeTicksToAbsoluteTicks(HundredsOfNanoseconds(frame.SystemRelativeTime().Value().count())).count();
            if (timestamp != pStreamer->m_latestTimestamp)
            {
                long long delta = timestamp - pStreamer->m_latestTimestamp;
                if (delta > pStreamer->m_minDelta)
                {
                    pStreamer->m_latestTimestamp = timestamp;
                    pStreamer->SendPvFrame(frame, timestamp);
                    pStreamer->m_writeInProgress = false;
                }
            }
        }
    }
}

void VideoFrameProcessor::SendPvFrame(winrt::Windows::Media::Capture::Frames::MediaFrameReference pFrame,long long pTimestamp)
{
#if DBG_ENABLE_INFO_LOGGING
    OutputDebugStringW(L"VideoCameraStreamer::SendFrame: Received frame for sending!\n");
#endif
    if (!m_StreamSocket || !m_writer)
    {
#if DBG_ENABLE_VERBOSE_LOGGING
        OutputDebugStringW(
            L"VideoCameraStreamer::SendFrame: No connection.\n");
#endif
        return;
    }
    if (!m_streamingEnabled)
    {
#if DBG_ENABLE_VERBOSE_LOGGING
        OutputDebugStringW(L"Streamer::SendFrame: Streaming disabled.\n");
#endif
        return;
    }

    // grab the frame info
    float fx = pFrame.VideoMediaFrame().CameraIntrinsics().FocalLength().x;
    float fy = pFrame.VideoMediaFrame().CameraIntrinsics().FocalLength().y;

    float ox = pFrame.VideoMediaFrame().CameraIntrinsics().PrincipalPoint().x;
    float oy = pFrame.VideoMediaFrame().CameraIntrinsics().PrincipalPoint().y;

    winrt::Windows::Foundation::Numerics::float4x4 PVtoWorldtransform;
    auto PVtoWorld =
        m_latestFrame.CoordinateSystem().TryGetTransformTo(m_worldCoordSystem);
    if (PVtoWorld)
    {
        PVtoWorldtransform = PVtoWorld.Value();
    }

    // grab the frame data
    SoftwareBitmap softwareBitmap = SoftwareBitmap::Convert(
        pFrame.VideoMediaFrame().SoftwareBitmap(), BitmapPixelFormat::Bgra8);

    int imageWidth = softwareBitmap.PixelWidth();
    int imageHeight = softwareBitmap.PixelHeight();

    int pixelStride = 4;
    int scaleFactor = 1;

    int rowStride = imageWidth * pixelStride;

    // Get bitmap buffer object of the frame
    BitmapBuffer bitmapBuffer = softwareBitmap.LockBuffer(BitmapBufferAccessMode::Read);

    // Get raw pointer to the buffer object
    uint32_t pixelBufferDataLength = 0;
    uint8_t* pixelBufferData;

    auto spMemoryBufferByteAccess{ bitmapBuffer.CreateReference()
        .as<::Windows::Foundation::IMemoryBufferByteAccess>() };

    try
    {
        spMemoryBufferByteAccess->
            GetBuffer(&pixelBufferData, &pixelBufferDataLength);
    }
    catch (winrt::hresult_error const& ex)
    {
#if DBG_ENABLE_ERROR_LOGGING
        winrt::hresult hr = ex.code(); // HRESULT_FROM_WIN32
        winrt::hstring message = ex.message();
        OutputDebugStringW(L"VideoCameraStreamer::SendFrame: Failed to get buffer with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
#endif
    }

    std::vector<uint8_t> imageBufferAsVector;
    for (int row = 0; row < imageHeight; row += scaleFactor)
    {
        for (int col = 0; col < rowStride; col += scaleFactor * pixelStride)
        {
            for (int j = 0; j < pixelStride - 1; j++)
            {
                imageBufferAsVector.emplace_back(
                    pixelBufferData[row * rowStride + col + j]);
            }
        }
    }


    if (m_writeInProgress)
    {
#if DBG_ENABLE_VERBOSE_LOGGING
        OutputDebugStringW(
            L"VideoCameraStreamer::SendFrame: Write in progress.\n");
#endif
        return;
    }
    m_writeInProgress = true;
    try
    {
        int outImageWidth = imageWidth / scaleFactor;
        int outImageHeight = imageHeight / scaleFactor;

        // pixel stride is reduced by 1 since we skip alpha channel
        int outPixelStride = pixelStride - 1;
        int outRowStride = outImageWidth * outPixelStride;


        // Write header
        m_writer.WriteUInt64(pTimestamp);
        m_writer.WriteInt32(outImageWidth);
        m_writer.WriteInt32(outImageHeight);
        m_writer.WriteInt32(outPixelStride);
        m_writer.WriteInt32(outRowStride);
        m_writer.WriteSingle(fx);
        m_writer.WriteSingle(fy);
        m_writer.WriteSingle(ox);
        m_writer.WriteSingle(oy);

        WriteMatrix4x4(PVtoWorldtransform);

        m_writer.WriteBytes(imageBufferAsVector);

#if DBG_ENABLE_VERBOSE_LOGGING
        OutputDebugStringW(L"VideoCameraStreamer::SendFrame: Trying to store writer...\n");
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
            m_StreamSocket == nullptr;
            m_writeInProgress = false;
        }
#if DBG_ENABLE_ERROR_LOGGING
        winrt::hstring message = ex.message();
        OutputDebugStringW(L"RMCameraStreamer::SendFrame: Sending failed with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
#endif // DBG_ENABLE_ERROR_LOGGING
    }
    catch (...)
    {
        // the client disconnected!
        m_writer == nullptr;
        m_StreamSocket == nullptr;
        m_writeInProgress = false;
    }
    m_writeInProgress = false;

#if DBG_ENABLE_VERBOSE_LOGGING
    OutputDebugStringW(
        L"VideoCameraStreamer::SendFrame: Frame sent!\n");
#endif

}


//void VideoFrameProcessor::CameraWriteThread(VideoFrameProcessor* pProcessor)
//{
//    while (!pProcessor->m_fExit)
//    {
//        std::lock_guard<std::mutex> guard(pProcessor->m_storageMutex);
//        if (pProcessor->m_storageFolder != nullptr)
//        {
//            SoftwareBitmap softwareBitmap = nullptr;
//            {
//                std::lock_guard<std::shared_mutex> lock(pProcessor->m_frameMutex);
//                if (pProcessor->m_latestFrame != nullptr)
//                {
//                    auto frame = pProcessor->m_latestFrame;
//                    long long timestamp = pProcessor->m_converter.RelativeTicksToAbsoluteTicks(HundredsOfNanoseconds(frame.SystemRelativeTime().Value().count())).count();
//                    if (timestamp != pProcessor->m_latestTimestamp)
//                    {
//                        softwareBitmap = SoftwareBitmap::Convert(frame.VideoMediaFrame().SoftwareBitmap(), BitmapPixelFormat::Bgra8);
//                        pProcessor->m_latestTimestamp = timestamp;
//                        pProcessor->AddLogFrame();
//                    }
//                }
//            }
//            // Convert and write the bitmap
//            if (softwareBitmap != nullptr)
//            {
//                pProcessor->DumpFrame(softwareBitmap, pProcessor->m_latestTimestamp);
//            }
//        }
//    }
//}

void VideoFrameProcessor::OnFrameArrived(const MediaFrameReader& sender, const MediaFrameArrivedEventArgs& args)
{
    if (MediaFrameReference frame = sender.TryAcquireLatestFrame())
    {    
        std::lock_guard<std::shared_mutex> lock(m_frameMutex);
        m_latestFrame = frame;
    }
}

void VideoFrameProcessor::Clear()
{
    std::lock_guard<std::shared_mutex> lock(m_frameMutex);
    m_PVFrameLog.clear();
}

void VideoFrameProcessor::AddLogFrame()
{
    // Lock on m_frameMutex from caller
    PVFrame frame;

    frame.timestamp = m_latestTimestamp;
    frame.fx = m_latestFrame.VideoMediaFrame().CameraIntrinsics().FocalLength().x;
    frame.fy = m_latestFrame.VideoMediaFrame().CameraIntrinsics().FocalLength().y;

    auto PVtoWorld = m_latestFrame.CoordinateSystem().TryGetTransformTo(m_worldCoordSystem);
    if (PVtoWorld)
    {
        frame.PVtoWorldtransform = PVtoWorld.Value();
    }
    m_PVFrameLog.push_back(std::move(frame));
}

void VideoFrameProcessor::DumpFrame(const SoftwareBitmap& softwareBitmap, long long timestamp)
{        
    // Compose the output file name
    wchar_t bitmapPath[MAX_PATH];
    swprintf_s(bitmapPath, L"%lld.%s", timestamp, L"bytes");

    // Get bitmap buffer object of the frame
    BitmapBuffer bitmapBuffer = softwareBitmap.LockBuffer(BitmapBufferAccessMode::Read);

    // Get raw pointer to the buffer object
    uint32_t pixelBufferDataLength = 0;
    uint8_t* pixelBufferData;

    auto spMemoryBufferByteAccess{ bitmapBuffer.CreateReference().as<::Windows::Foundation::IMemoryBufferByteAccess>() };
    winrt::check_hresult(spMemoryBufferByteAccess->GetBuffer(&pixelBufferData, &pixelBufferDataLength));

    m_tarball->AddFile(bitmapPath, &pixelBufferData[0], pixelBufferDataLength);    
}

bool VideoFrameProcessor::DumpDataToDisk(const StorageFolder& folder, const std::wstring& datetime_path)
{
    auto path = folder.Path().data();
    std::wstring fullName(path);
    fullName += L"\\" + datetime_path + L"_pv.txt";
    std::ofstream file(fullName);
    if (!file)
    {
        return false;
    }
    
    std::lock_guard<std::shared_mutex> lock(m_frameMutex);
    // assuming this is called at the end of the capture session, and m_latestFrame is not nullptr
    assert(m_latestFrame != nullptr); 
    file << m_latestFrame.VideoMediaFrame().CameraIntrinsics().PrincipalPoint().x << "," << m_latestFrame.VideoMediaFrame().CameraIntrinsics().PrincipalPoint().y << ","
         << m_latestFrame.VideoMediaFrame().CameraIntrinsics().ImageWidth() << "," << m_latestFrame.VideoMediaFrame().CameraIntrinsics().ImageHeight() << "\n";
    
    for (const PVFrame& frame : m_PVFrameLog)
    {
        file << frame.timestamp << ",";
        file << frame.fx << "," << frame.fy << ",";
        file << frame.PVtoWorldtransform.m11 << "," << frame.PVtoWorldtransform.m21 << "," << frame.PVtoWorldtransform.m31 << "," << frame.PVtoWorldtransform.m41 << ","
            << frame.PVtoWorldtransform.m12 << "," << frame.PVtoWorldtransform.m22 << "," << frame.PVtoWorldtransform.m32 << "," << frame.PVtoWorldtransform.m42 << ","
            << frame.PVtoWorldtransform.m13 << "," << frame.PVtoWorldtransform.m23 << "," << frame.PVtoWorldtransform.m33 << "," << frame.PVtoWorldtransform.m43 << ","
            << frame.PVtoWorldtransform.m14 << "," << frame.PVtoWorldtransform.m24 << "," << frame.PVtoWorldtransform.m34 << "," << frame.PVtoWorldtransform.m44;
        file << "\n";
    }
    file.close();
    return true;
}

void VideoFrameProcessor::StartRecording(const SpatialCoordinateSystem& worldCoordSystem)
{
    m_worldCoordSystem = worldCoordSystem;
}

void VideoFrameProcessor::StopRecording()
{ // TODO need to reset something?
}
bool VideoFrameProcessor::getWriterState()
{
    if (!m_StreamSocket || !m_writer)
    {
        return false;
    }
    return true;
}
void VideoFrameProcessor::CameraWriteThread(VideoFrameProcessor* pProcessor)
{
    while (!pProcessor->m_fExit)
    {
        std::lock_guard<std::mutex> guard(pProcessor->m_storageMutex);
        if (pProcessor->m_storageFolder != nullptr)
        {
            SoftwareBitmap softwareBitmap = nullptr;
            {
                std::lock_guard<std::shared_mutex> lock(pProcessor->m_frameMutex);
                if (pProcessor->m_latestFrame != nullptr)
                {
                    auto frame = pProcessor->m_latestFrame;                    
                    long long timestamp = pProcessor->m_converter.RelativeTicksToAbsoluteTicks(HundredsOfNanoseconds(frame.SystemRelativeTime().Value().count())).count();
                    if (timestamp != pProcessor->m_latestTimestamp)
                    {
                        softwareBitmap = SoftwareBitmap::Convert(frame.VideoMediaFrame().SoftwareBitmap(), BitmapPixelFormat::Bgra8);
                        pProcessor->m_latestTimestamp = timestamp;
                        pProcessor->AddLogFrame();
                    }
                }
            }
            // Convert and write the bitmap
            if (softwareBitmap != nullptr)
            {
                pProcessor->DumpFrame(softwareBitmap, pProcessor->m_latestTimestamp);
            }
        }
    }
}


void VideoFrameProcessor::WriteMatrix4x4(
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