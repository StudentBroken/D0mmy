# Module Index
> Last indexed: 2026-04-22T04:36:21.013925+00:00  |  Workspace: `/Users/xumic/Developer/SafeReps`

---

## `analysis/exercise-logic` — Exercise Logic
> Defines exercise configurations, rep counting logic, and joint angle selectors for movement analysis.

**Files:** `safereps/lib/analysis/exercise.dart`  `safereps/lib/analysis/rep_counter.dart`

```
safereps/lib/analysis/exercise.dart
├── Exercise:8 — Configuration for a specific physical exercise
│   ├── Exercise:36 — Constructor
└── builtInExercises:83 — List of predefined Exercise configurations
```

```
safereps/lib/analysis/rep_counter.dart
├── RepResult:21 — Result object containing rep count and current phase
└── RepCounter:37 — State machine for tracking exercise repetitions
    ├── update:38 — Updates rep state based on current joint angles
    └── _nextPhase:57 — Transitions the state machine to the next rep phase
```

---

## `analysis/imu-form-tracking` — IMU Form Tracking
> Analyzes IMU data from wearable sensors to track exercise form quality and detect violations.

**Files:** `safereps/lib/analysis/exercise_imu_profile.dart`  `safereps/lib/analysis/rep_form_tracker.dart`
**Deps:** services/ble-service

```
exercise_imu_profile.dart
├── ExerciseImuProfile:2 — IMU quality parameter configuration
│   └── copyWith:26 — Creates a copy with updated thresholds
├── lateralRaiseImuProfile:42 — IMU profile for Lateral Raise
├── bicepCurlImuProfile:54 — IMU profile for Bicep Curl
└── imuProfileForExercise:67 — Maps exercise name to its IMU profile
```

```
safereps/lib/analysis/rep_form_tracker.dart
├── RepFormResult:4 — Data model for a single rep's form metrics
└── RepFormTracker:24 — Logic for tracking and deducting form quality
```

---

## `pose/camera-analysis` — Pose Camera Analysis
> Manages real-time camera streaming, pose estimation, and skeleton rendering for exercise tracking.

**Files:** `safereps/lib/pose_camera_page.dart`  `safereps/lib/pose_painter.dart`

```
pose_camera_page.dart
├── PoseCameraPage:20 — Page widget for real-time pose tracking
│   └── createState:26 — Creates the state for PoseCameraPage
└── _PoseCameraPageState:29 — State handler for camera and pose detection
    ├── SkeletonSmoother:40 — Smoothes skeleton joint positions
    ├── _bootstrap:73 — Initializes permissions and camera setup
    ├── _setError:74 — Sets error state for UI display
    ├── _startCamera:103 — Configures and starts the camera stream
    ├── MlKitPoseEstimator:141 — Initializes the ML Kit pose detector
    ├── availableCameras:156 — Queries available device cameras
    ├── _switchCamera:206 — Toggles between available cameras
    ├── RepCounter:220 — Manages rep counting for active exercise
    ├── _copyAngles:231 — Updates current joint angles
    ├── _onCameraImage:251 — Processes each camera frame for pose
    ├── _buildFrameMeta:256 — Constructs frame metadata
    ├── computeJointAngles:273 — Calculates angles between joints
    └── FrameMeta:274 — Data holder for frame-specific pose info
└── _ExercisePanel:482 — UI panel to select and display exercises
└── _ExerciseTile:528 — UI tile for individual exercise items
```

```
safereps/lib/pose_painter.dart
├── PosePainter:9 — CustomPainter for drawing pose skeletons
│   ├── paint:27 — Renders joints, bones, and angles
│   ├── _drawAngles:50 — Paints joint angle labels on canvas
│   ├── _project:68 — Maps landmark coordinates to canvas offset
│   ├── _tx:89 — Translates X coordinate based on rotation/lens
│   └── _bonePaint:126 — Creates paint object for skeleton bones
└── FrameMeta:148 — Metadata for image size, rotation, and lens
```

---

## `pages/dashboard` — Dashboard
> Main hub for tracking exercise progress, device connectivity, and starting training sessions.

**Files:** `safereps/lib/pages/dashboard_page.dart`
**Deps:** services/ble-service

```
dashboard_page.dart
├── DashboardPage:19 — Main dashboard screen widget
│   └── createState:23 — Creates the state for DashboardPage
├── _DashboardPageState:26 — State for DashboardPage with pulse animation
│   ├── AnimationController:34 — Controls the start button pulse effect
│   └── CurvedAnimation:39 — Defines the pulse animation curve
├── _DashHeader:151 — Header widget showing greetings and BLE status
│   └── Expanded:162 — Layout wrapper for greeting text
├── _BlePill:175 — Connectivity status indicator for BLE device
│   └── Color:194 — Determines pill color based on connection/battery
├── _BleConnectSheet:264 — Bottom sheet for managing BLE connections
│   └── createState:269 — Creates the state for the connection sheet
├── _BleConnectSheetState:272 — State for managing BLE scan and connection
├── _SheetConnectedBody:399 — UI for currently connected BLE device
│   ├── _getBattColor:406 — Returns color based on battery voltage
│   ├── GlassCard:419 — Container for connection details
│   ├── Row:425 — Layout for battery/signal indicators
│   ├── Container:427 — Wrapper for status icon
│   ├── Expanded:434 — Space filler for layout
│   ├── Row:447 — Row for signal strength and battery
│   ├── Icon:449 — Signal strength indicator
│   ├── Expanded:451 — Space filler for layout
│   ├── Row:455 — Row for battery percentage/voltage
│   ├── Text:457 — Battery voltage display
│   ├── Text:465 — Connectivity status text
│   ├── _battLabel:466 — Helper for battery text label
│   ├── ClipRRect:476 — Visual wrapper for battery bar
│   ├── AlwaysStoppedAnimation:483 — Static value for battery progress
│   ├── Text:493 — Battery percentage text
│   └── RoundedRectangleBorder:507 — Border for the battery card
└── _SheetReconnectBody:541 — UI for reconnecting to a BLE device
    └── SizedBox:554 — Spacer for layout
```

---

## `pages/games` — Exercise Games
> Implements game-based exercises using IMU or ML-based pose detection.

**Files:** `safereps/lib/pages/game67_page.dart`

```
safereps/lib/pages/game67_page.dart
├── _HandTracker:41 — Tracks hand raise/return cycles for ML mode
├── Game67Page:61 — StatefulWidget for the game interface
└── _Game67PageState:68 — State manager for camera, pose, and game logic
    ├── SkeletonSmoother:79 — Smooths skeletal pose data
    ├── _loadBest:122 — Loads best score from preferences
    ├── _bootstrap:123 — Initializes permissions and camera
    ├── _saveBest:170 — Saves high score to preferences
    ├── _queryCameras:198 — Fetches available camera devices
    ├── MlKitPoseEstimator:208 — Initializes the ML Kit pose estimator
    ├── _startCamera:224 — Configures and starts camera stream
    ├── _onFrame:261 — Processes camera frames for pose detection
    ├── _buildMeta:265 — Generates metadata for the current frame
    ├── _calcElevation:283 — Calculates relative wrist height
    ├── _maybeUpdateBest:307 — Updates best score if current is higher
    ├── _buildHud:462 — Builds the game HUD overlay
    ├── _ModeToggle:476 — UI widget to toggle between IMU and ML modes
    ├── _PitchBar:534 — Visual indicator for pitch tracking
    ├── _HandBars:545 — Visual indicator for hand elevations
    └── _HudButton:558 — Generic HUD action button
```

---

## `services/ble-service` — BLE Service
> Handles Bluetooth Low Energy connectivity, device discovery, and IMU data streaming.

**Files:** `safereps/lib/services/ble_service.dart`

```
safereps/lib/services/ble_service.dart
├── ImuData:10 — Data model for IMU sensor readings and battery
└── BleService:77 — Manages BLE connections and IMU data streams
    ├── _init:113 — Initializes saved device and starts auto-reconnect
    ├── _persistDevice:131 — Saves device ID and name to shared preferences
    ├── forgetDevice:142 — Removes saved device and disconnects
    ├── _cancelReconnect:148 — Stops the auto-reconnection loop
    ├── startScan:157 — Scans for available BLE devices
    ├── stopScan:180 — Stops the BLE scan
    ├── connect:190 — Initiates a connection to a specific device
    ├── _doConnect:197 — Low-level BLE connection and service discovery
    ├── disconnect:209 — Disconnects from the current BLE device
    ├── _onLinkLost:233 — Handles unexpected connection loss
    ├── _startAutoReconnect:300 — Loop for reconnecting with exponential backoff
    ├── _cancellableSleep:339 — Sleep utility for reconnection loops
    ├── _hardDisconnect:346 — Cleans up connection and subscriptions
    ├── sendCommand:393 — Sends a text command to the BLE device
    ├── toggleStream:400 — Toggles the IMU data stream
    ├── startImuStream:406 — Starts streaming IMU data
    ├── stopImuStream:413 — Stops streaming IMU data
    ├── zero:420 — Sends zeroing command to device
    ├── resetCalibration:422 — Sends calibration reset command
    ├── setTremorHp:424 — Sets the high-pass filter for tremor
    ├── setTremorEma:427 — Sets the exponential moving average for tremor
    └── setCheatEps:430 — Sets the epsilon for cheat detection
```

---

## `services/theme-service` — Theme Service
> Manages application theme flavor and persistence.

**Files:** `safereps/lib/services/theme_service.dart`  `safereps/lib/theme.dart`

```
safereps/lib/services/theme_service.dart
├── ThemeService:5 — Manages and persists application theme flavor
│   ├── init:11 — Loads saved theme flavor from SharedPreferences
│   └── setFlavor:23 — Updates theme flavor and persists it
└── ThemeScope:33 — InheritedNotifier for providing ThemeService to the widget tree
    └── of:40 — Returns the ThemeService instance from context
```

```
safereps/lib/theme.dart
├── AppColors:5 — Static constants for general and fallback pink theme colors
│   └── Color:7 — Constant color values
├── AppTheme:23 — Theme configuration and factory methods
│   ├── fromFlavor:24 — Generates ThemeData based on ThemeFlavor
│   └── colors:107 — Accesses BrandColors from the current context
└── BrandColors:113 — ThemeExtension for custom brand-specific colors
```

---

## `services/voice-coach` — Voice Coach Service
> Handles audio cue playback and coaching track management.

**Files:** `safereps/lib/services/voice_coach_service.dart`

```
safereps/lib/services/voice_coach_service.dart
├── CueCategory:16 — Enum for audio trigger categories
└── VoiceCoachService:421
    ├── play:449 — Plays a cue from a specific category
    ├── _nextTrack:466 — Selects next non-repeating track in pool
    ├── _toSentenceCase:475 — Formats track names for UI display
    ├── playCorrection:504 — Plays a correction cue based on exercise
    └── playMandatory:508 — Plays a required audio cue
```

---

## `ui/shell-and-layout` — Shell and Layout
> Implements the app's main navigation shell and reusable glassmorphism UI components.

**Files:** `safereps/lib/shell.dart`  `safereps/lib/widgets/glass_card.dart`
**Deps:** pages/dashboard, services/theme-service

```
safereps/lib/shell.dart
├── MainShell:31 — Main app shell with PageView navigation
│   └── createState:35 — Creates the shell state
├── _MainShellState:38 — State management for MainShell
│   └── PageController:40 — Controller for page transitions
├── _FloatingNav:102 — Glassmorphism floating navigation bar
│   ├── BoxShadow:132 — Outer diffuse shadow
│   ├── BoxShadow:140 — iOS specific depth shadow
│   ├── BackdropFilter:153 — Background blur layer
│   ├── CustomPaint:167 — Specular and caustic effects
│   ├── Padding:170 — Layout for navigation bubble
│   ├── Padding:180 — Layout for navigation items
│   └── Positioned:197 — Container for rep speed pill
├── _LiquidGlassPainter:215 — Custom painter for glass effects
│   ├── _paintIOS:227 — Renders iOS glass highlights
│   └── _paintAndroid:229 — Renders Android glass highlights
├── _NavBubble:351 — Sliding indicator for the active nav item
├── _NavItem:409 — Individual navigation tab button
│   └── createState:421 — Creates the item state
├── _NavItemState:424 — State for animation of nav items
│   └── AnimationController:431 — Handles item transition animation
└── _RepSpeedPill:486 — Indicator for current repetition speed
    └── _colorForSpeed:492 — Returns color based on speed value
```

```
safereps/lib/widgets/glass_card.dart
├── GlassCard:8 — Frosted-glass morphism card widget
```

---

## `app/core` — App Core
> Main entry point and root widget managing dependency injection and application bootstrap.

**Files:** `safereps/lib/main.dart`
**Deps:** services/ble-service, services/theme-service

```
safereps/lib/main.dart
├── main:15 — app entry point and dependency initialization
└── SafeRepsApp:61 — root app widget with theme management
```

---

## `build/generated-plugins` — Generated Plugins
> Generated files for registering Flutter plugins across different platforms.

**Files:** `safereps/.dart_tool/dartpad/web_plugin_registrant.dart`  `safereps/.dart_tool/flutter_build/dart_plugin_registrant.dart`

```
safereps/.dart_tool/dartpad/web_plugin_registrant.dart
└── registerPlugins:18 — Registers all web-specific plugins for the application
```

```
safereps/.dart_tool/flutter_build/dart_plugin_registrant.dart
├── _PluginRegistrant:35 — Generated class to register platform plugins
│   ├── register:38 — Registers plugins based on the current platform
│   └── print:43 — Logs plugin registration errors
```

---

## `tooling/ios-helpers` — iOS Helpers
> LLDB Python helper script for Flutter iOS build debugging.

**Files:** `safereps/ios/Flutter/ephemeral/flutter_lldb_helper.py`

```
safereps/ios/Flutter/ephemeral/flutter_lldb_helper.py
├── handle_new_rx_page:7 — intercept RX pages and write identity marker
└── __lldb_init_module:24 — initialize LLDB breakpoint and script callback
```

---

## `tooling/esp32-scripts` — ESP32 Scripts
> Script to inject battery monitoring logic into ESP32 C++ source code.

**Files:** `update_batt.py`

```
update_batt.py
└── (no symbols detected)
```

---

## `test/integration` — Integration Tests
> Widget tests to verify the basic application boot sequence.

**Files:** `safereps/test/widget_test.dart`
**Deps:** app/core

```
safereps/test/widget_test.dart
├── testWidgets:6 — verifies app boots and renders the main title
└── SafeRepsApp:7 — root widget of the application
└── expect:8 — asserts that a specific widget is found
```

---
