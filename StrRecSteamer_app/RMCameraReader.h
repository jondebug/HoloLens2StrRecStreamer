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

#include "researchmode\ResearchModeApi.h"
#include "Tar.h"
#include "TimeConverter.h"
#include "../Cannon/MixedReality.h"
#include <MemoryBuffer.h>
#include <winrt/Windows.Media.Devices.Core.h>
#include <winrt/Windows.Media.Capture.Frames.h>
#include <winrt/Windows.Graphics.Imaging.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <mutex>
#include <winrt/Windows.Perception.Spatial.h>
#include <winrt/Windows.Perception.Spatial.Preview.h>
#include <winrt/Windows.Storage.Streams.h>
#include <winrt/Windows.Networking.Sockets.h>


// Struct to store per-frame rig2world transformations
// See also https://docs.microsoft.com/en-us/windows/mixed-reality/locatable-camera
struct FrameLocation
{
	long long timestamp;	
	winrt::Windows::Foundation::Numerics::float4x4 rigToWorldtransform;
};


class RMCameraReader
{
public:
	RMCameraReader(IResearchModeSensor* pLLSensor, HANDLE camConsentGiven, ResearchModeSensorConsent* camAccessConsent, const GUID& guid,MixedReality* mixedReality)
	{
		m_pRMSensor = pLLSensor;
		m_pRMSensor->AddRef();
		m_pSensorFrame = nullptr;

		// Get GUID identifying the rigNode to
		// initialize the SpatialLocator
		SetLocator(guid);
		// Reserve for 10 seconds at 30fps (holds for VLC)
		//m_frameLocations.reserve(10 * 30);
		m_worldCoordSystem = mixedReality->GetWorldCoordinateSystem();
		InitializeAsync(0, m_worldCoordSystem, L"23941");

		m_pCameraUpdateThread = new std::thread(CameraUpdateThread, this, camConsentGiven, camAccessConsent);

		//m_pWriteThread = new std::thread(CameraWriteThread, this);
		//m_pStreamThread = new std::thread(CameraSendThread, this);
	}

	void SetStorageFolder(const winrt::Windows::Storage::StorageFolder& storageFolder);
	void SetWorldCoordSystem(const winrt::Windows::Perception::Spatial::SpatialCoordinateSystem& coordSystem);
	void ResetStorageFolder();	
	winrt::Windows::Foundation::IAsyncAction StartServer();

	void InitializeAsync(
		const long long minDelta,
		const winrt::Windows::Perception::Spatial::SpatialCoordinateSystem& coordSystem,
		std::wstring portName);

	virtual ~RMCameraReader()
	{
		m_fExit = true;
		m_pCameraUpdateThread->join();

		if (m_pRMSensor)
		{
			m_pRMSensor->CloseStream();
			m_pRMSensor->Release();
		}

		m_pWriteThread->join();
	}	
	bool getWriterState();
protected:
	// Thread for retrieving frames
	static void CameraUpdateThread(RMCameraReader* pReader, HANDLE camConsentGiven, ResearchModeSensorConsent* camAccessConsent);
	// Thread for writing frames to disk
	static void CameraWriteThread(RMCameraReader* pReader);
	static void CameraSendThread(RMCameraReader* pReader);

	bool IsNewTimestamp(IResearchModeSensorFrame* pSensorFrame);

	void SaveFrame(IResearchModeSensorFrame* pSensorFrame);
	void SaveVLC(IResearchModeSensorFrame* pSensorFrame, IResearchModeSensorVLCFrame* pVLCFrame);
	void SaveDepth(IResearchModeSensorFrame* pSensorFrame, IResearchModeSensorDepthFrame* pDepthFrame);

	void DumpCalibration();
	void OnConnectionReceived(
		winrt::Windows::Networking::Sockets::StreamSocketListener sender,
		winrt::Windows::Networking::Sockets::StreamSocketListenerConnectionReceivedEventArgs args);
	void SetLocator(const GUID& guid);
	bool AddFrameLocation();
	void DumpFrameLocations();
	void WriteMatrix4x4(_In_ winrt::Windows::Foundation::Numerics::float4x4 matrix);
	// Mutex to access sensor frame
	std::mutex m_sensorFrameMutex;
	IResearchModeSensor* m_pRMSensor = nullptr;
	IResearchModeSensorFrame* m_pSensorFrame = nullptr;

	bool m_fExit = false;
	std::thread* m_pCameraUpdateThread;
	std::thread* m_pWriteThread;

	//LUT
	std::vector<unsigned char> m_lutTableByteData;

	// streaming thread
	std::thread* m_pStreamThread = nullptr;

	// socket, listener and writer
	winrt::Windows::Networking::Sockets::StreamSocketListener m_streamSocketListener;
	winrt::Windows::Networking::Sockets::StreamSocket m_streamSocket = nullptr;
	winrt::Windows::Storage::Streams::DataWriter m_writer;
	bool m_writeInProgress = false;
	bool m_streamingEnabled = true;
	bool m_isExtrinsicsSent = false;
	// Mutex to access storage folder
	std::mutex m_storageMutex;
	// conditional variable to enable / disable writing to disk
	std::condition_variable m_storageCondVar;	
	winrt::Windows::Storage::StorageFolder m_storageFolder = nullptr;
	std::unique_ptr<Io::Tarball> m_tarball;

	TimeConverter m_converter;
	UINT64 m_prevTimestamp = 0;

	std::wstring m_portName;
	// minDelta allows to enforce a certain time delay between frames
	// should be set in hundreds of nanoseconds (ms * 1e-4)
	long long m_minDelta;

	winrt::Windows::Perception::Spatial::SpatialLocator m_locator = nullptr;
	winrt::Windows::Perception::Spatial::SpatialCoordinateSystem m_worldCoordSystem = nullptr;
	//std::vector<FrameLocation> m_frameLocations;	
};
