from collections import namedtuple, deque

wrong_format = "@2q881fcccc"

EYE_STREAM_HEADER_FORMAT = "@2q16f4f4f4f416f416f16?" #only added the last 4 c's for allignment to cpp struct.

EYE_FRAME_STREAM = namedtuple(
     'EYEStreamPacket',
     #timestamp 2 x long long:
     'timestamp timestamp_placekeeper0 '
     #HeadTransform 16 x float:
     'HeadTransformM11 HeadTransformM12 HeadTransformM13 HeadTransformM14  '
     'HeadTransformM21 HeadTransformM22 HeadTransformM23 HeadTransformM24  '
     'HeadTransformM31 HeadTransformM32 HeadTransformM33 HeadTransformM34  '
     'HeadTransformM41 HeadTransformM42 HeadTransformM43 HeadTransformM44  '
     #eye gaze origin 4 x float:
     'eyeGazeOriginM11 eyeGazeOriginM12 eyeGazeOriginM13 eyeGazeOriginM14  '
     #eye gaze direction 4 x float:
     'eyeGazeDirectionM11 eyeGazeDirectionM12 eyeGazeDirectionM13 eyeGazeDirectionM14 '
     #eye gaze distance 4 x float:
     'eyeGazeDistance eyeGazeDistance_placekeeper0 eyeGazeDistance_placekeeper1 eyeGazeDistance_placekeeper2 '
     #left hand transform 416 x float:
     'L_Palm11 L_Palm12 L_Palm13 L_Palm14 '
     'L_Palm21 L_Palm22 L_Palm23 L_Palm24 '
     'L_Palm31 L_Palm32 L_Palm33 L_Palm34 '
     'L_Palm41 L_Palm42 L_Palm43 L_Palm44 '
     'L_Wrist11 L_Wrist12 L_Wrist13 L_Wrist14 '
     'L_Wrist21 L_Wrist22 L_Wrist23 L_Wrist24 '
     'L_Wrist31 L_Wrist32 L_Wrist33 L_Wrist34 '
     'L_Wrist41 L_Wrist42 L_Wrist43 L_Wrist44 '
     'L_ThumbMetacarpal11 L_ThumbMetacarpal12 L_ThumbMetacarpal13 L_ThumbMetacarpal14 '
     'L_ThumbMetacarpal21 L_ThumbMetacarpal22 L_ThumbMetacarpal23 L_ThumbMetacarpal24 '
     'L_ThumbMetacarpal31 L_ThumbMetacarpal32 L_ThumbMetacarpal33 L_ThumbMetacarpal34 '
     'L_ThumbMetacarpal41 L_ThumbMetacarpal42 L_ThumbMetacarpal43 L_ThumbMetacarpal44 '
     'L_ThumbProximal11 L_ThumbProximal12 L_ThumbProximal13 L_ThumbProximal14 '
     'L_ThumbProximal21 L_ThumbProximal22 L_ThumbProximal23 L_ThumbProximal24 '
     'L_ThumbProximal31 L_ThumbProximal32 L_ThumbProximal33 L_ThumbProximal34 '
     'L_ThumbProximal41 L_ThumbProximal42 L_ThumbProximal43 L_ThumbProximal44 '
     'L_ThumbDistal11 L_ThumbDistal12 L_ThumbDistal13 L_ThumbDistal14 '
     'L_ThumbDistal21 L_ThumbDistal22 L_ThumbDistal23 L_ThumbDistal24 '
     'L_ThumbDistal31 L_ThumbDistal32 L_ThumbDistal33 L_ThumbDistal34 '
     'L_ThumbDistal41 L_ThumbDistal42 L_ThumbDistal43 L_ThumbDistal44 '
     'L_ThumbTip11 L_ThumbTip12 L_ThumbTip13 L_ThumbTip14 '
     'L_ThumbTip21 L_ThumbTip22 L_ThumbTip23 L_ThumbTip24 '
     'L_ThumbTip31 L_ThumbTip32 L_ThumbTip33 L_ThumbTip34 '
     'L_ThumbTip41 L_ThumbTip42 L_ThumbTip43 L_ThumbTip44 '
     'L_IndexMetacarpal11 L_IndexMetacarpal12 L_IndexMetacarpal13 L_IndexMetacarpal14 '
     'L_IndexMetacarpal21 L_IndexMetacarpal22 L_IndexMetacarpal23 L_IndexMetacarpal24 '
     'L_IndexMetacarpal31 L_IndexMetacarpal32 L_IndexMetacarpal33 L_IndexMetacarpal34 '
     'L_IndexMetacarpal41 L_IndexMetacarpal42 L_IndexMetacarpal43 L_IndexMetacarpal44 '
     'L_IndexProximal11 L_IndexProximal12 L_IndexProximal13 L_IndexProximal14 '
     'L_IndexProximal21 L_IndexProximal22 L_IndexProximal23 L_IndexProximal24 '
     'L_IndexProximal31 L_IndexProximal32 L_IndexProximal33 L_IndexProximal34 '
     'L_IndexProximal41 L_IndexProximal42 L_IndexProximal43 L_IndexProximal44 '
     'L_IndexIntermediate11 L_IndexIntermediate12 L_IndexIntermediate13 L_IndexIntermediate14 '
     'L_IndexIntermediate21 L_IndexIntermediate22 L_IndexIntermediate23 L_IndexIntermediate24 '
     'L_IndexIntermediate31 L_IndexIntermediate32 L_IndexIntermediate33 L_IndexIntermediate34 '
     'L_IndexIntermediate41 L_IndexIntermediate42 L_IndexIntermediate43 L_IndexIntermediate44 '
     'L_IndexDistal11 L_IndexDistal12 L_IndexDistal13 L_IndexDistal14 '
     'L_IndexDistal21 L_IndexDistal22 L_IndexDistal23 L_IndexDistal24 '
     'L_IndexDistal31 L_IndexDistal32 L_IndexDistal33 L_IndexDistal34 '
     'L_IndexDistal41 L_IndexDistal42 L_IndexDistal43 L_IndexDistal44 '
     'L_IndexTip11 L_IndexTip12 L_IndexTip13 L_IndexTip14 '
     'L_IndexTip21 L_IndexTip22 L_IndexTip23 L_IndexTip24 '
     'L_IndexTip31 L_IndexTip32 L_IndexTip33 L_IndexTip34 '
     'L_IndexTip41 L_IndexTip42 L_IndexTip43 L_IndexTip44 '
     'L_MiddleMetacarpal11 L_MiddleMetacarpal12 L_MiddleMetacarpal13 L_MiddleMetacarpal14 '
     'L_MiddleMetacarpal21 L_MiddleMetacarpal22 L_MiddleMetacarpal23 L_MiddleMetacarpal24 '
     'L_MiddleMetacarpal31 L_MiddleMetacarpal32 L_MiddleMetacarpal33 L_MiddleMetacarpal34 '
     'L_MiddleMetacarpal41 L_MiddleMetacarpal42 L_MiddleMetacarpal43 L_MiddleMetacarpal44 '
     'L_MiddleProximal11 L_MiddleProximal12 L_MiddleProximal13 L_MiddleProximal14 '
     'L_MiddleProximal21 L_MiddleProximal22 L_MiddleProximal23 L_MiddleProximal24 '
     'L_MiddleProximal31 L_MiddleProximal32 L_MiddleProximal33 L_MiddleProximal34 '
     'L_MiddleProximal41 L_MiddleProximal42 L_MiddleProximal43 L_MiddleProximal44 '
     'L_MiddleIntermediate11 L_MiddleIntermediate12 L_MiddleIntermediate13 L_MiddleIntermediate14 '
     'L_MiddleIntermediate21 L_MiddleIntermediate22 L_MiddleIntermediate23 L_MiddleIntermediate24 '
     'L_MiddleIntermediate31 L_MiddleIntermediate32 L_MiddleIntermediate33 L_MiddleIntermediate34 '
     'L_MiddleIntermediate41 L_MiddleIntermediate42 L_MiddleIntermediate43 L_MiddleIntermediate44 '
     'L_MiddleDistal11 L_MiddleDistal12 L_MiddleDistal13 L_MiddleDistal14 '
     'L_MiddleDistal21 L_MiddleDistal22 L_MiddleDistal23 L_MiddleDistal24 '
     'L_MiddleDistal31 L_MiddleDistal32 L_MiddleDistal33 L_MiddleDistal34 '
     'L_MiddleDistal41 L_MiddleDistal42 L_MiddleDistal43 L_MiddleDistal44 '
     'L_MiddleTip11 L_MiddleTip12 L_MiddleTip13 L_MiddleTip14 '
     'L_MiddleTip21 L_MiddleTip22 L_MiddleTip23 L_MiddleTip24 '
     'L_MiddleTip31 L_MiddleTip32 L_MiddleTip33 L_MiddleTip34 '
     'L_MiddleTip41 L_MiddleTip42 L_MiddleTip43 L_MiddleTip44 '
     'L_RingMetacarpal11 L_RingMetacarpal12 L_RingMetacarpal13 L_RingMetacarpal14 '
     'L_RingMetacarpal21 L_RingMetacarpal22 L_RingMetacarpal23 L_RingMetacarpal24 '
     'L_RingMetacarpal31 L_RingMetacarpal32 L_RingMetacarpal33 L_RingMetacarpal34 '
     'L_RingMetacarpal41 L_RingMetacarpal42 L_RingMetacarpal43 L_RingMetacarpal44 '
     'L_RingProximal11 L_RingProximal12 L_RingProximal13 L_RingProximal14 '
     'L_RingProximal21 L_RingProximal22 L_RingProximal23 L_RingProximal24 '
     'L_RingProximal31 L_RingProximal32 L_RingProximal33 L_RingProximal34 '
     'L_RingProximal41 L_RingProximal42 L_RingProximal43 L_RingProximal44 '
     'L_RingIntermediate11 L_RingIntermediate12 L_RingIntermediate13 L_RingIntermediate14 '
     'L_RingIntermediate21 L_RingIntermediate22 L_RingIntermediate23 L_RingIntermediate24 '
     'L_RingIntermediate31 L_RingIntermediate32 L_RingIntermediate33 L_RingIntermediate34 '
     'L_RingIntermediate41 L_RingIntermediate42 L_RingIntermediate43 L_RingIntermediate44 '
     'L_RingDistal11 L_RingDistal12 L_RingDistal13 L_RingDistal14 '
     'L_RingDistal21 L_RingDistal22 L_RingDistal23 L_RingDistal24 '
     'L_RingDistal31 L_RingDistal32 L_RingDistal33 L_RingDistal34 '
     'L_RingDistal41 L_RingDistal42 L_RingDistal43 L_RingDistal44 '
     'L_RingTip11 L_RingTip12 L_RingTip13 L_RingTip14 '
     'L_RingTip21 L_RingTip22 L_RingTip23 L_RingTip24 '
     'L_RingTip31 L_RingTip32 L_RingTip33 L_RingTip34 '
     'L_RingTip41 L_RingTip42 L_RingTip43 L_RingTip44 '
     'L_PinkyMetacarpal11 L_PinkyMetacarpal12 L_PinkyMetacarpal13 L_PinkyMetacarpal14 '
     'L_PinkyMetacarpal21 L_PinkyMetacarpal22 L_PinkyMetacarpal23 L_PinkyMetacarpal24 '
     'L_PinkyMetacarpal31 L_PinkyMetacarpal32 L_PinkyMetacarpal33 L_PinkyMetacarpal34 '
     'L_PinkyMetacarpal41 L_PinkyMetacarpal42 L_PinkyMetacarpal43 L_PinkyMetacarpal44 '
     'L_PinkyProximal11 L_PinkyProximal12 L_PinkyProximal13 L_PinkyProximal14 '
     'L_PinkyProximal21 L_PinkyProximal22 L_PinkyProximal23 L_PinkyProximal24 '
     'L_PinkyProximal31 L_PinkyProximal32 L_PinkyProximal33 L_PinkyProximal34 '
     'L_PinkyProximal41 L_PinkyProximal42 L_PinkyProximal43 L_PinkyProximal44 '
     'L_PinkyIntermediate11 L_PinkyIntermediate12 L_PinkyIntermediate13 L_PinkyIntermediate14 '
     'L_PinkyIntermediate21 L_PinkyIntermediate22 L_PinkyIntermediate23 L_PinkyIntermediate24 '
     'L_PinkyIntermediate31 L_PinkyIntermediate32 L_PinkyIntermediate33 L_PinkyIntermediate34 '
     'L_PinkyIntermediate41 L_PinkyIntermediate42 L_PinkyIntermediate43 L_PinkyIntermediate44 '
     'L_PinkyDistal11 L_PinkyDistal12 L_PinkyDistal13 L_PinkyDistal14 '
     'L_PinkyDistal21 L_PinkyDistal22 L_PinkyDistal23 L_PinkyDistal24 '
     'L_PinkyDistal31 L_PinkyDistal32 L_PinkyDistal33 L_PinkyDistal34 '
     'L_PinkyDistal41 L_PinkyDistal42 L_PinkyDistal43 L_PinkyDistal44 '
     'L_PinkyTip11 L_PinkyTip12 L_PinkyTip13 L_PinkyTip14 '
     'L_PinkyTip21 L_PinkyTip22 L_PinkyTip23 L_PinkyTip24 '
     'L_PinkyTip31 L_PinkyTip32 L_PinkyTip33 L_PinkyTip34 '
     'L_PinkyTip41 L_PinkyTip42 L_PinkyTip43 L_PinkyTip44 '
     #Right hand transform 416 x float:
     'R_Palm11 R_Palm12 R_Palm13 R_Palm14 '
     'R_Palm21 R_Palm22 R_Palm23 R_Palm24 '
     'R_Palm31 R_Palm32 R_Palm33 R_Palm34 '
     'R_Palm41 R_Palm42 R_Palm43 R_Palm44 '
     'R_Wrist11 R_Wrist12 R_Wrist13 R_Wrist14 '
     'R_Wrist21 R_Wrist22 R_Wrist23 R_Wrist24 '
     'R_Wrist31 R_Wrist32 R_Wrist33 R_Wrist34 '
     'R_Wrist41 R_Wrist42 R_Wrist43 R_Wrist44 '
     'R_ThumbMetacarpal11 R_ThumbMetacarpal12 R_ThumbMetacarpal13 R_ThumbMetacarpal14 '
     'R_ThumbMetacarpal21 R_ThumbMetacarpal22 R_ThumbMetacarpal23 R_ThumbMetacarpal24 '
     'R_ThumbMetacarpal31 R_ThumbMetacarpal32 R_ThumbMetacarpal33 R_ThumbMetacarpal34 '
     'R_ThumbMetacarpal41 R_ThumbMetacarpal42 R_ThumbMetacarpal43 R_ThumbMetacarpal44 '
     'R_ThumbProximal11 R_ThumbProximal12 R_ThumbProximal13 R_ThumbProximal14 '
     'R_ThumbProximal21 R_ThumbProximal22 R_ThumbProximal23 R_ThumbProximal24 '
     'R_ThumbProximal31 R_ThumbProximal32 R_ThumbProximal33 R_ThumbProximal34 '
     'R_ThumbProximal41 R_ThumbProximal42 R_ThumbProximal43 R_ThumbProximal44 '
     'R_ThumbDistal11 R_ThumbDistal12 R_ThumbDistal13 R_ThumbDistal14 '
     'R_ThumbDistal21 R_ThumbDistal22 R_ThumbDistal23 R_ThumbDistal24 '
     'R_ThumbDistal31 R_ThumbDistal32 R_ThumbDistal33 R_ThumbDistal34 '
     'R_ThumbDistal41 R_ThumbDistal42 R_ThumbDistal43 R_ThumbDistal44 '
     'R_ThumbTip11 R_ThumbTip12 R_ThumbTip13 R_ThumbTip14 '
     'R_ThumbTip21 R_ThumbTip22 R_ThumbTip23 R_ThumbTip24 '
     'R_ThumbTip31 R_ThumbTip32 R_ThumbTip33 R_ThumbTip34 '
     'R_ThumbTip41 R_ThumbTip42 R_ThumbTip43 R_ThumbTip44 '
     'R_IndexMetacarpal11 R_IndexMetacarpal12 R_IndexMetacarpal13 R_IndexMetacarpal14 '
     'R_IndexMetacarpal21 R_IndexMetacarpal22 R_IndexMetacarpal23 R_IndexMetacarpal24 '
     'R_IndexMetacarpal31 R_IndexMetacarpal32 R_IndexMetacarpal33 R_IndexMetacarpal34 '
     'R_IndexMetacarpal41 R_IndexMetacarpal42 R_IndexMetacarpal43 R_IndexMetacarpal44 '
     'R_IndexProximal11 R_IndexProximal12 R_IndexProximal13 R_IndexProximal14 '
     'R_IndexProximal21 R_IndexProximal22 R_IndexProximal23 R_IndexProximal24 '
     'R_IndexProximal31 R_IndexProximal32 R_IndexProximal33 R_IndexProximal34 '
     'R_IndexProximal41 R_IndexProximal42 R_IndexProximal43 R_IndexProximal44 '
     'R_IndexIntermediate11 R_IndexIntermediate12 R_IndexIntermediate13 R_IndexIntermediate14 '
     'R_IndexIntermediate21 R_IndexIntermediate22 R_IndexIntermediate23 R_IndexIntermediate24 '
     'R_IndexIntermediate31 R_IndexIntermediate32 R_IndexIntermediate33 R_IndexIntermediate34 '
     'R_IndexIntermediate41 R_IndexIntermediate42 R_IndexIntermediate43 R_IndexIntermediate44 '
     'R_IndexDistal11 R_IndexDistal12 R_IndexDistal13 R_IndexDistal14 '
     'R_IndexDistal21 R_IndexDistal22 R_IndexDistal23 R_IndexDistal24 '
     'R_IndexDistal31 R_IndexDistal32 R_IndexDistal33 R_IndexDistal34 '
     'R_IndexDistal41 R_IndexDistal42 R_IndexDistal43 R_IndexDistal44 '
     'R_IndexTip11 R_IndexTip12 R_IndexTip13 R_IndexTip14 '
     'R_IndexTip21 R_IndexTip22 R_IndexTip23 R_IndexTip24 '
     'R_IndexTip31 R_IndexTip32 R_IndexTip33 R_IndexTip34 '
     'R_IndexTip41 R_IndexTip42 R_IndexTip43 R_IndexTip44 '
     'R_MiddleMetacarpal11 R_MiddleMetacarpal12 R_MiddleMetacarpal13 R_MiddleMetacarpal14 '
     'R_MiddleMetacarpal21 R_MiddleMetacarpal22 R_MiddleMetacarpal23 R_MiddleMetacarpal24 '
     'R_MiddleMetacarpal31 R_MiddleMetacarpal32 R_MiddleMetacarpal33 R_MiddleMetacarpal34 '
     'R_MiddleMetacarpal41 R_MiddleMetacarpal42 R_MiddleMetacarpal43 R_MiddleMetacarpal44 '
     'R_MiddleProximal11 R_MiddleProximal12 R_MiddleProximal13 R_MiddleProximal14 '
     'R_MiddleProximal21 R_MiddleProximal22 R_MiddleProximal23 R_MiddleProximal24 '
     'R_MiddleProximal31 R_MiddleProximal32 R_MiddleProximal33 R_MiddleProximal34 '
     'R_MiddleProximal41 R_MiddleProximal42 R_MiddleProximal43 R_MiddleProximal44 '
     'R_MiddleIntermediate11 R_MiddleIntermediate12 R_MiddleIntermediate13 R_MiddleIntermediate14 '
     'R_MiddleIntermediate21 R_MiddleIntermediate22 R_MiddleIntermediate23 R_MiddleIntermediate24 '
     'R_MiddleIntermediate31 R_MiddleIntermediate32 R_MiddleIntermediate33 R_MiddleIntermediate34 '
     'R_MiddleIntermediate41 R_MiddleIntermediate42 R_MiddleIntermediate43 R_MiddleIntermediate44 '
     'R_MiddleDistal11 R_MiddleDistal12 R_MiddleDistal13 R_MiddleDistal14 '
     'R_MiddleDistal21 R_MiddleDistal22 R_MiddleDistal23 R_MiddleDistal24 '
     'R_MiddleDistal31 R_MiddleDistal32 R_MiddleDistal33 R_MiddleDistal34 '
     'R_MiddleDistal41 R_MiddleDistal42 R_MiddleDistal43 R_MiddleDistal44 '
     'R_MiddleTip11 R_MiddleTip12 R_MiddleTip13 R_MiddleTip14 '
     'R_MiddleTip21 R_MiddleTip22 R_MiddleTip23 R_MiddleTip24 '
     'R_MiddleTip31 R_MiddleTip32 R_MiddleTip33 R_MiddleTip34 '
     'R_MiddleTip41 R_MiddleTip42 R_MiddleTip43 R_MiddleTip44 '
     'R_RingMetacarpal11 R_RingMetacarpal12 R_RingMetacarpal13 R_RingMetacarpal14 '
     'R_RingMetacarpal21 R_RingMetacarpal22 R_RingMetacarpal23 R_RingMetacarpal24 '
     'R_RingMetacarpal31 R_RingMetacarpal32 R_RingMetacarpal33 R_RingMetacarpal34 '
     'R_RingMetacarpal41 R_RingMetacarpal42 R_RingMetacarpal43 R_RingMetacarpal44 '
     'R_RingProximal11 R_RingProximal12 R_RingProximal13 R_RingProximal14 '
     'R_RingProximal21 R_RingProximal22 R_RingProximal23 R_RingProximal24 '
     'R_RingProximal31 R_RingProximal32 R_RingProximal33 R_RingProximal34 '
     'R_RingProximal41 R_RingProximal42 R_RingProximal43 R_RingProximal44 '
     'R_RingIntermediate11 R_RingIntermediate12 R_RingIntermediate13 R_RingIntermediate14 '
     'R_RingIntermediate21 R_RingIntermediate22 R_RingIntermediate23 R_RingIntermediate24 '
     'R_RingIntermediate31 R_RingIntermediate32 R_RingIntermediate33 R_RingIntermediate34 '
     'R_RingIntermediate41 R_RingIntermediate42 R_RingIntermediate43 R_RingIntermediate44 '
     'R_RingDistal11 R_RingDistal12 R_RingDistal13 R_RingDistal14 '
     'R_RingDistal21 R_RingDistal22 R_RingDistal23 R_RingDistal24 '
     'R_RingDistal31 R_RingDistal32 R_RingDistal33 R_RingDistal34 '
     'R_RingDistal41 R_RingDistal42 R_RingDistal43 R_RingDistal44 '
     'R_RingTip11 R_RingTip12 R_RingTip13 R_RingTip14 '
     'R_RingTip21 R_RingTip22 R_RingTip23 R_RingTip24 '
     'R_RingTip31 R_RingTip32 R_RingTip33 R_RingTip34 '
     'R_RingTip41 R_RingTip42 R_RingTip43 R_RingTip44 '
     'R_PinkyMetacarpal11 R_PinkyMetacarpal12 R_PinkyMetacarpal13 R_PinkyMetacarpal14 '
     'R_PinkyMetacarpal21 R_PinkyMetacarpal22 R_PinkyMetacarpal23 R_PinkyMetacarpal24 '
     'R_PinkyMetacarpal31 R_PinkyMetacarpal32 R_PinkyMetacarpal33 R_PinkyMetacarpal34 '
     'R_PinkyMetacarpal41 R_PinkyMetacarpal42 R_PinkyMetacarpal43 R_PinkyMetacarpal44 '
     'R_PinkyProximal11 R_PinkyProximal12 R_PinkyProximal13 R_PinkyProximal14 '
     'R_PinkyProximal21 R_PinkyProximal22 R_PinkyProximal23 R_PinkyProximal24 '
     'R_PinkyProximal31 R_PinkyProximal32 R_PinkyProximal33 R_PinkyProximal34 '
     'R_PinkyProximal41 R_PinkyProximal42 R_PinkyProximal43 R_PinkyProximal44 '
     'R_PinkyIntermediate11 R_PinkyIntermediate12 R_PinkyIntermediate13 R_PinkyIntermediate14 '
     'R_PinkyIntermediate21 R_PinkyIntermediate22 R_PinkyIntermediate23 R_PinkyIntermediate24 '
     'R_PinkyIntermediate31 R_PinkyIntermediate32 R_PinkyIntermediate33 R_PinkyIntermediate34 '
     'R_PinkyIntermediate41 R_PinkyIntermediate42 R_PinkyIntermediate43 R_PinkyIntermediate44 '
     'R_PinkyDistal11 R_PinkyDistal12 R_PinkyDistal13 R_PinkyDistal14 '
     'R_PinkyDistal21 R_PinkyDistal22 R_PinkyDistal23 R_PinkyDistal24 '
     'R_PinkyDistal31 R_PinkyDistal32 R_PinkyDistal33 R_PinkyDistal34 '
     'R_PinkyDistal41 R_PinkyDistal42 R_PinkyDistal43 R_PinkyDistal44 '
     'R_PinkyTip11 R_PinkyTip12 R_PinkyTip13 R_PinkyTip14 '
     'R_PinkyTip21 R_PinkyTip22 R_PinkyTip23 R_PinkyTip24 '
     'R_PinkyTip31 R_PinkyTip32 R_PinkyTip33 R_PinkyTip34 '
     'R_PinkyTip41 R_PinkyTip42 R_PinkyTip43 R_PinkyTip44 '
     
     #Boolean Parameters 3 x Bool: 
     'leftHandPresent rightHandPresent eyeGazePresent '
     
     #boolean placekeepers 13 x Bool:
     'Bool_pk_0 Bool_pk_1 Bool_pk_2 Bool_pk_3 '
     'Bool_pk_4 Bool_pk_5 Bool_pk_6 Bool_pk_7 '
     'Bool_pk_8 Bool_pk_9 Bool_pk_10 Bool_pk_11 '
     'Bool_pk_12 '
    )

