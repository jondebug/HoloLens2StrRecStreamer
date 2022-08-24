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

#include "HeTHaTEyeStream.h"

#include <winrt/Windows.Storage.h>
#include <fstream>
#include <iomanip>

using namespace DirectX;
using namespace winrt::Windows::Storage;
using namespace winrt::Windows::Networking::Sockets;
using namespace winrt::Windows::Storage::Streams;

HeTHaTEyeStream::HeTHaTEyeStream()
{
    // reserve for 10 seconds at 60fps
    m_hethateyeLog.reserve(10 * 60); 
    m_hethateyeLogOrig.reserve(10 * 60);
    m_eyeDataCounter = 0;
}

void HeTHaTEyeStream::AddFrame(HeTHaTEyeFrameOrig&& frame)
{
    m_hethateyeLogOrig.push_back(std::move(frame));
}

void HeTHaTEyeStream::SendFrame(HeTHaTEyeFrame& pFrame)
{
    OutputDebugStringW(L"EyeStreamer::SendFrame: Received eye for sending!\n");
    if (!m_streamSocket || !m_writer)
    {
        OutputDebugStringW(
            L"EyeStreamer::SendFrame: No connection.\n");
        return;
    }
    if (!m_streamingEnabled)
    {
        OutputDebugStringW(L"Streamer::SendFrame: Streaming disabled.\n");
        return;
    }
    //m_writer.WriteBytes();
    //std::vector<BYTE> EyeByteData;
    int size = sizeof pFrame;
    auto ptr = reinterpret_cast<BYTE*>(&pFrame);
    auto EyeByteData = std::vector<BYTE>(ptr, ptr + sizeof pFrame);

    m_writeInProgress = true;
    try
    {
        m_writer.WriteBytes(EyeByteData);
        OutputDebugStringW(L"EyeStreamer::EyeSendFrame: Trying to store writer...\n");
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
        winrt::hstring message = ex.message();
        OutputDebugStringW(L"Eye streamer :: SendFrame- Sending failed with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
    }
    catch(...)
    {
            // the client disconnected!
            m_writer == nullptr;
            m_streamSocket == nullptr;
            m_writeInProgress = false;
            OutputDebugStringW(L"Eye streamer :: Connection is closed ");
    }
    OutputDebugStringW(L"EyeGaze - Frame sent!\n");
    m_writeInProgress = false;
    //this is how we rebuild the data on the client side: auto p_obj = reinterpret_cast<obj_t*>(&buffer[0]);
}
void HeTHaTEyeStream::Clear()
{
    m_hethateyeLog.clear();
    m_hethateyeLogOrig.clear();
}

size_t HeTHaTEyeStream::FrameCount() const
{
    return m_hethateyeLog.size();
}

const std::vector<HeTHaTEyeFrame>& HeTHaTEyeStream::Log() const
{
    return m_hethateyeLog;
}

std::ostream& operator<<(std::ostream& out, const XMMATRIX& m)
{
    XMFLOAT4X4 mView;
    XMStoreFloat4x4(&mView, m);
    for (int j = 0; j < 4; ++j)
    {
        for (int i = 0; i < 4; ++i)
        {
            out << std::setprecision(8) << mView.m[i][j];
            if (i < 3 || j < 3)
            {
                out << ",";
            }
        }
    }
    return out;
}

std::ostream& operator<<(std::ostream& out, const XMVECTOR& v)
{
    XMFLOAT4 mView;
    XMStoreFloat4(&mView, v);
    
    out << std::setprecision(8) << mView.x << "," << mView.y << "," << mView.z << "," << mView.w;

    return out;
}

void DumpHandIfPresentElseZero(bool present, const XMMATRIX& handTransform, std::ostream& out)
{
    static const float zeros[16] = { 0.0 };
    static const XMMATRIX zero4x4(zeros);
    if (present)
    {
        out << handTransform;
    }
    else
    {
        out << zero4x4;
    }
}

void DumpEyeGazeIfPresentElseZero(bool present, const XMVECTOR& origin, const XMVECTOR& direction, float distance, std::ostream& out)
{
    XMFLOAT4 zeros{ 0, 0, 0, 0 };
    XMVECTOR zero4 = XMLoadFloat4(&zeros);
    out << present << ",";
    if (present)
    {
        out << origin << "," << direction;
    }
    else
    {
        out << zero4 << "," << zero4;
    }
    out << "," << distance;
}

bool HeTHaTEyeStream::DumpToDisk(const StorageFolder& folder, const std::wstring& datetime_path) const
{  
    auto path = folder.Path().data();
    std::wstring fullName(path);
    fullName += +L"\\" + datetime_path + L"_head_hand_eye.csv";
    std::ofstream file(fullName);
    if (!file)
    {
        return false;
    }

    for (const HeTHaTEyeFrameOrig& frame : m_hethateyeLogOrig)
    {
        file << frame.timestamp << ",";
        file << frame.headTransform;
        file << ",";
        file << frame.leftHandPresent;
        for (int j = 0; j < (int)HandJointIndex::Count; ++j)
        {
            file << ",";
            DumpHandIfPresentElseZero(frame.leftHandPresent, frame.leftHandTransform[j], file);
        }
        file << ",";
        file << frame.rightHandPresent;
        for (int j = 0; j < (int)HandJointIndex::Count; ++j)
        {
            file << ",";
            DumpHandIfPresentElseZero(frame.rightHandPresent, frame.rightHandTransform[j], file);
        }
        file << ",";
        DumpEyeGazeIfPresentElseZero(frame.eyeGazePresent, frame.eyeGazeOrigin, frame.eyeGazeDirection, frame.eyeGazeDistance, file);
        file << std::endl;
    }
    file.close();
    return true;
}

bool HeTHaTEyeStream::DumpTransformToDisk(const XMMATRIX& mtx, const StorageFolder& folder, const std::wstring& datetime_path, const std::wstring& suffix) const
{
    auto path = folder.Path().data();
    std::wstring fullName(path);
    fullName += +L"\\" + datetime_path + suffix;
    std::ofstream file(fullName);
    if (!file)
    {
        return false;
    }
    file << mtx;
    file.close();
    return true;
}

void HeTHaTEyeStream::InitializeAsync(const long long minDelta,std::wstring portName)
{
    OutputDebugStringW(L"EyeStreamer::InitializeAsync: Creating Eye Streamer\n");

    m_portName = portName;
    m_minDelta = minDelta;

    m_streamingEnabled = true;

    StartEyeStreamServer();

    //m_pStreamThread = new std::thread(HeTHaTEyeStream::GetAndSendThread, this);
    //m_pEyeCollenctionThread  = new std::thread(GetEyeGazeThread, this);
    //m_OnFrameArrivedRegistration = mediaFrameReader.FrameArrived({ this, &VideoCameraStreamer::OnFrameArrived });
}

winrt::Windows::Foundation::IAsyncAction HeTHaTEyeStream::StartEyeStreamServer()
{
    try
    {
        // The ConnectionReceived event is raised when connections are received.
        m_streamSocketListener.ConnectionReceived({ this, &HeTHaTEyeStream::OnConnectionReceived });

        // Start listening for incoming TCP connections on the specified port. You can specify any port that's not currently in use.
        // Every protocol typically has a standard port number. For example, HTTP is typically 80, FTP is 20 and 21, etc.
        // For this example, we'll choose an arbitrary port number.
        co_await m_streamSocketListener.BindServiceNameAsync(m_portName);
        //m_streamSocketListener.Control().KeepAlive(true);

        wchar_t msgBuffer[200];
        swprintf_s(msgBuffer, L"Eye gaze handler: Server is listening at %ls \n",
            m_portName.c_str());
        OutputDebugStringW(msgBuffer);
    }
    catch (winrt::hresult_error const& ex)
    {

        SocketErrorStatus webErrorStatus{ SocketError::GetStatus(ex.to_abi()) };
        winrt::hstring message = webErrorStatus != SocketErrorStatus::Unknown ?
            winrt::to_hstring((int32_t)webErrorStatus) : winrt::to_hstring(ex.to_abi());
        OutputDebugStringW(L"EyeGazeThread::StartServer: Failed to open listener with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");

    }
}


void HeTHaTEyeStream::OnConnectionReceived(
    StreamSocketListener sender,
    StreamSocketListenerConnectionReceivedEventArgs args)
{
    try
    {
        m_streamSocket = args.Socket();
        m_writer = (winrt::Windows::Storage::Streams::DataWriter)args.Socket().OutputStream();
        m_writer.UnicodeEncoding(UnicodeEncoding::Utf8);
        m_writer.ByteOrder(ByteOrder::LittleEndian);
        //TODO: 
        //args.Socket().Information()
        m_writeInProgress = false;
        OutputDebugStringW(L"EyeGazeStreamer::OnConnectionReceived: Received connection! \n");
    }
    catch (winrt::hresult_error const& ex)
    {
        SocketErrorStatus webErrorStatus{ SocketError::GetStatus(ex.to_abi()) };
        winrt::hstring message = webErrorStatus != SocketErrorStatus::Unknown ?
            winrt::to_hstring((int32_t)webErrorStatus) : winrt::to_hstring(ex.to_abi());
        OutputDebugStringW(L"EyeGaze::StartServer: Failed to open listener with ");
        OutputDebugStringW(message.c_str());
        OutputDebugStringW(L"\n");
    }
}


HeTHaTStreamVisualizer::HeTHaTStreamVisualizer()
{
}

void HeTHaTStreamVisualizer::Draw()
{
    for (auto drawCall : m_drawCalls)
    {
        drawCall->Draw();
    }
}

void HeTHaTStreamVisualizer::Update(const HeTHaTEyeStream& stream)
{
    m_drawCalls.clear();
    
    const XMMATRIX scale = XMMatrixScaling(0.03f, 0.03f, 0.03f);
    for (int i_frame = 0; i_frame < stream.FrameCount(); i_frame += kStride)
    {
        const HeTHaTEyeFrame& frame = stream.Log()[i_frame];

        auto drawCallLeft = std::make_shared<DrawCall>("Lit_VS.cso", "Lit_PS.cso", Mesh::MT_PLANE);
        drawCallLeft->SetWorldTransform(scale * frame.leftHandTransform[(int)HandJointIndex::Palm]);
        drawCallLeft->SetColor(XMVectorSet(1.0f, 0.0f, 0.0f, 1.0f));
        m_drawCalls.push_back(drawCallLeft);

        auto drawCallRight = std::make_shared<DrawCall>("Lit_VS.cso", "Lit_PS.cso", Mesh::MT_PLANE);
        drawCallRight->SetWorldTransform(scale * frame.rightHandTransform[(int)HandJointIndex::Palm]);
        drawCallRight->SetColor(XMVectorSet(0.0f, 1.0f, 0.0f, 1.0f));
        m_drawCalls.push_back(drawCallRight);

        auto drawCallHead = std::make_shared<DrawCall>("Lit_VS.cso", "Lit_PS.cso", Mesh::MT_UIPLANE);
        drawCallHead->SetWorldTransform(scale * frame.headTransform);
        drawCallHead->SetColor(XMVectorSet(0.0f, 0.0f, 1.0f, 1.0f));
        m_drawCalls.push_back(drawCallHead);
    }
}

