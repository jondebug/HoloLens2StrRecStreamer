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

#pragma once

#include <vector>
#include "../Cannon/DrawCall.h"
#include "../Cannon/MixedReality.h"
#include <winrt/Windows.Networking.Sockets.h>
#include <winrt/Windows.Storage.Streams.h>
#include <winrt/Windows.Foundation.Collections.h>

//__declspec(align(16))
struct HeTHaTEyeFrameOrig
{
    DirectX::XMMATRIX headTransform;
    std::array<DirectX::XMMATRIX, (size_t)HandJointIndex::Count> leftHandTransform;
    std::array<DirectX::XMMATRIX, (size_t)HandJointIndex::Count> rightHandTransform;
    DirectX::XMVECTOR eyeGazeOrigin;
    DirectX::XMVECTOR eyeGazeDirection;
    float eyeGazeDistance;
    bool leftHandPresent;
    bool rightHandPresent;
    bool eyeGazePresent;
    long long timestamp;
};

__declspec(align(16))
volatile struct HeTHaTEyeFrame
{
    long long timestamp[2];					//16B = 2*8B
    DirectX::XMMATRIX headTransform;		//64B = 16*4B
    DirectX::XMVECTOR eyeGazeOrigin;		//16B = 4*4B
    DirectX::XMVECTOR eyeGazeDirection;		//16B = 4*4B
    float eyeGazeDistance[4];				//16B = 4*4B
    std::array<DirectX::XMMATRIX, (size_t)HandJointIndex::Count> leftHandTransform;			//26*16*4 = 1664	//array of length count = 26 and data type XMMATRIX. XMMATRIX is a 4x4 matrix of floats
    std::array<DirectX::XMMATRIX, (size_t)HandJointIndex::Count> rightHandTransform;		//26*16*4 = 1664
    //bool leftHandPresent;					//1B
    //bool rightHandPresent;				//1B
    //bool eyeGazePresent;					//1B
    bool left_pres_right_pres_eye_pres_free_bytes[16];//16B = 16*1B = 

};

class HeTHaTEyeStream
{
public:
    HeTHaTEyeStream();

    void AddFrame(HeTHaTEyeFrameOrig&& frame);
    void Clear();
    const std::vector<HeTHaTEyeFrame>& Log() const;
    size_t FrameCount() const;
    bool DumpToDisk(const winrt::Windows::Storage::StorageFolder& folder, const std::wstring& datetime_path) const;
    bool DumpTransformToDisk(const DirectX::XMMATRIX& mtx, const winrt::Windows::Storage::StorageFolder& folder,
                             const std::wstring& datetime_path, const std::wstring& suffix) const;
    void HeTHaTEyeStream::InitializeAsync(const long long minDelta,std::wstring portName);
    void OnConnectionReceived(
        winrt::Windows::Networking::Sockets::StreamSocketListener sender,
        winrt::Windows::Networking::Sockets::StreamSocketListenerConnectionReceivedEventArgs args);

    winrt::Windows::Foundation::IAsyncAction HeTHaTEyeStream::StartEyeStreamServer();

    void SendFrame(HeTHaTEyeFrame& pFrame);
    // streaming
    winrt::Windows::Networking::Sockets::StreamSocketListener m_streamSocketListener;
    winrt::Windows::Networking::Sockets::StreamSocket m_streamSocket = nullptr;
    winrt::Windows::Storage::Streams::DataWriter m_writer = nullptr;
    bool m_writeInProgress = false;

    std::wstring m_portName;
    // minDelta allows to enforce a certain time delay between frames
    // should be set in hundreds of nanoseconds (ms * 1e-4)
    long long m_minDelta;
    bool m_streamingEnabled = true;
    int m_eyeDataCounter;
private:
    std::vector<HeTHaTEyeFrame> m_hethateyeLog;
    std::vector<HeTHaTEyeFrameOrig> m_hethateyeLogOrig;
};

class HeTHaTStreamVisualizer
{
public:
    HeTHaTStreamVisualizer();

    void Draw();
    void Update(const HeTHaTEyeStream& stream);

private:
    static const int kStride = 10;

    std::vector<std::shared_ptr<DrawCall>> m_drawCalls;
};
