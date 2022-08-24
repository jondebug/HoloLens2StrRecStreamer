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
#include "RMCameraReader.h"
#include "../Cannon/MixedReality.h"

class SensorScenario
{
public:
	SensorScenario(const std::vector<ResearchModeSensorType>& kEnabledSensorTypes);
	virtual ~SensorScenario();

	void InitializeSensors();
	void InitializeCameraReaders(MixedReality* mixedReality);
	void StartRecording(const winrt::Windows::Perception::Spatial::SpatialCoordinateSystem& worldCoordSystem);
	void StopRecording();
	static void CamAccessOnComplete(ResearchModeSensorConsent consent);
	bool getWriterState();
private:
	void GetRigNodeId(GUID& outGuid) const;

	const std::vector<ResearchModeSensorType>& m_kEnabledSensorTypes;
	std::vector<std::shared_ptr<RMCameraReader>> m_cameraReaders;
	
	std::shared_ptr<RMCameraReader> m_pAHATProcessor;
	std::shared_ptr<RMCameraReader> m_pLONGTHROWProcessor;

	IResearchModeSensorDevice* m_pSensorDevice = nullptr;
	IResearchModeSensorDeviceConsent* m_pSensorDeviceConsent = nullptr;
	MixedReality* m_mixedReality=nullptr;
	std::vector<ResearchModeSensorDescriptor> m_sensorDescriptors;
	// Supported RM sensors
	IResearchModeSensor* m_pLFCameraSensor = nullptr;
	IResearchModeSensor* m_pRFCameraSensor = nullptr;
	IResearchModeSensor* m_pLLCameraSensor = nullptr;
	IResearchModeSensor* m_pRRCameraSensor = nullptr;
	IResearchModeSensor* m_pLTSensor = nullptr;
	IResearchModeSensor* m_pAHATSensor = nullptr;		
};
