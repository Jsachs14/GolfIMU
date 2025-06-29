# GolfIMU
A controls system and kalman filtering approach to fixing Jonah's golf game (and getting Noah to swing a golf club)






#SOFTWARE LAYOUT 

-->Embedded Software (Arduino C)
    -->Radio Capabilities
    -->IMU Processing
    -->Power Distribution
    -->Battery Level Modeling
    -->Timing and Throughout Analysis
    -->Swing Detection and Buffering
    -->Complete Swing Data Transmission

--> Backend (Python) (Temporary Redis Database) (may eventually send to web app if data is too big)
    -->Process Complete Swing Data from Arduino
    -->Store Complete Swings in Redis Database for extended kalman filtering and physical analysis for quantities presented in latex doc
    -->Send Redis values to a persistent time series database (eventually?)


#BACKEND STRUCTURE

The backend is organized into modular components:

-->Core Modules
    -->config.py - Configuration settings and environment variables
    -->models.py - Pydantic data models for IMU data, swings, sessions, and events
    -->redis_manager.py - Redis operations for swing data storage and retrieval
    -->serial_manager.py - Arduino serial communication and swing data parsing
    -->session_manager.py - User session management and club configurations
    -->main.py - Main application that ties everything together

-->Key Features
    -->Session Management - Create sessions with user_id, club_id, club specifications
    -->Complete Swing Data - Receive and store entire swings with all IMU data points
    -->Swing-Based Processing - Process complete swings instead of real-time streaming
    -->Session Persistence - Store session configs and swing data in Redis
    -->Swing Statistics - Calculate swing metrics and statistics

-->Data Flow
    -->Arduino buffers complete swing data with timestamps
    -->After impact detection, Arduino sends entire swing as JSON
    -->Python backend receives and stores complete swing in Redis
    -->Swing data includes all IMU readings, timing, and metadata

-->Usage
    -->Install dependencies: pip install -r requirements.txt
    -->Start Redis server: brew services start redis (Mac) or docker run -d -p 6379:6379 redis:alpine
    -->Run backend: python run_backend.py
    -->Commands: start_session, connect_arduino, send_config, start_monitoring, wait_swing, continuous_monitoring, status, summary, statistics, recent_swings, quit


PHYSICAL ANALYZER FUNCTIONS 

-->Sensor Fusion Module
    -->Madgwick/Kalman Filter Implementation
        - Process complete swing IMU data for quaternion updates
        - Redis: Store processed swing data with session_id, user_id, club_id, timestamp
        - Database fields: session_id, user_id, club_id, swing_id, quaternions, euler_angles, ts
    -->Quaternion to Euler Angle Conversion
        - Convert qSI to roll-pitch-yaw using QuatToEuler function
        - Redis: Store quaternions and Euler angles with swing data
        - Database fields: swing_id, qw, qx, qy, qz, roll, pitch, yaw, ts
    -->Rotation Matrix Calculations (RSI)
        - Compute 3x3 rotation matrix from quaternion for kinematic calculations
        - Redis: Cache rotation matrices for efficient head speed calculations
        - Database fields: swing_id, R11, R12, R13, R21, R22, R23, R31, R32, R33, ts
    -->9-DOF IMU Data Processing (ax, ay, az, gx, gy, gz, mx, my, mz)
        - Validate sensor data ranges and detect sensor faults
        - Redis: Store complete swing IMU data with session identification
        - Session controls: user_id, club_id, session_id, club_length, face_normal_calibration

-->Timing Analysis Module
    -->Backswing Time Detection (Tb) - First sign change of ωz
        - Analyze complete swing data for sign changes during swing
        - Redis: Store swing events with session_id, event_type, timestamp
        - Database fields: session_id, swing_id, Tb, start_time, top_time, ts
    -->Downswing Time Detection (Td) - Top to impact interval
        - Track time from backswing peak to impact detection
        - Redis: Calculate and store tempo metrics per swing
        - Database fields: session_id, swing_id, Td, impact_time, tempo_ratio, ts
    -->Tempo Ratio Calculation (Tb:Td) - Target 3:1 ratio
        - Compute ratio and compare against ideal 3:1 backswing:downswing
        - Redis: Store tempo analysis with swing quality scoring
        - Database fields: session_id, swing_id, Tb, Td, tempo_ratio, tempo_score, ts
    -->Impact Detection via g-threshold
        - Detect impact when |a| exceeds configurable threshold (default 30g)
        - Redis: Store impact detection with swing metadata
        - Session controls: impact_threshold, user_id, club_id, session_id

-->Speed & Power Module
    -->Club Head Speed Calculation (vh = ||ωI × RSI·r||)
        - Apply rigid body kinematics using lever arm and angular velocity
        - Redis: Store head speed time-series with session identification
        - Database fields: session_id, swing_id, v_head, vx, vy, vz, ts
    -->Peak G-Force Detection (max |a| per swing)
        - Track maximum acceleration magnitude during each swing
        - Redis: Store peak values with swing data
        - Database fields: session_id, swing_id, g_peak, g_peak_time, ts
    -->Centripetal Force Calculation (Fc = m·ℓ·ωz²)
        - Calculate shaft loading using club mass and angular velocity
        - Redis: Store force calculations for structural analysis
        - Database fields: session_id, swing_id, F_cent, club_mass, lever_arm, ts
    -->Lever Arm Kinematics (r = [0,0,-ℓ])
        - Apply club-specific lever arm for accurate head speed calculation
        - Session controls: club_id, club_length, club_mass, user_id, session_id

-->Path & Plane Analysis Module
    -->Swing Plane Tilt (β) - PCA on shaft axis during downswing
        - Perform principal component analysis on shaft direction vectors
        - Redis: Store PCA results with swing data
        - Database fields: session_id, swing_id, plane_tilt_beta, pca_eigenvalues, ts
    -->Attack Angle (α) - Vertical component of head velocity
        - Calculate vertical component of club head velocity at impact
        - Redis: Store attack angle with swing path analysis
        - Database fields: session_id, swing_id, attack_angle_alpha, v_vertical, ts
    -->Club Path (γ) - Azimuth of head velocity in ground plane
        - Compute horizontal direction of club head movement
        - Redis: Store path analysis for draw/fade detection
        - Database fields: session_id, swing_id, club_path_gamma, v_horizontal, ts
    -->Face Angle (δ) - Rotated face normal calibration
        - Apply stored face normal calibration to current rotation
        - Session controls: face_normal_calibration, club_id, user_id, session_id
        - Database fields: session_id, swing_id, face_angle_delta, face_normal_I, ts

-->Quality Metrics Module
    -->Release Frame Detection - Zero-crossing of angular acceleration
        - Monitor angular acceleration for release timing analysis
        - Redis: Store release events with swing timing analysis
        - Database fields: session_id, swing_id, release_time, release_frame, ts
    -->Smoothness Calculation (S) - Integrated squared jerk
        - Integrate squared jerk over swing duration for smoothness metric
        - Redis: Store smoothness scores for swing comparison
        - Database fields: session_id, swing_id, smoothness_S, jerk_integral, ts
    -->Impact FFT Analysis - Power spectral density around impact
        - Perform FFT on acceleration data ±3ms around impact
        - Redis: Store frequency domain analysis for contact quality
        - Database fields: session_id, swing_id, impact_fft, psd_data, ts
    -->Swing Consistency Scoring
        - Compare current swing metrics to user's historical data
        - Session controls: user_id, historical_baseline, consistency_threshold
        - Database fields: session_id, swing_id, consistency_score, metric_deviations, ts

-->Data Management Module
    -->Redis Swing Storage
        - Organize swing data by session_id with user_id and club_id prefixes
        - Redis structure: session:{session_id}:user:{user_id}:club:{club_id}:swings
        - Session controls: session_id, user_id, club_id, session_start_time
    -->Swing Data Management
        - Store complete swings with all IMU data points and metadata
        - Redis: Efficient storage and retrieval of complete swing data
        - Database fields: session_id, swing_id, imu_data_points, swing_metadata, ts
    -->Complete Swing Processing
        - Process entire swings for comprehensive analysis
        - Redis: Store processed swing data with analysis results
        - Session controls: swing_count, swing_statistics, processing_results
    -->Metric Export and Persistence
        - Export calculated metrics to persistent time-series database
        - Redis: Batch export completed swing data with session metadata
        - Database fields: session_id, user_id, club_id, export_timestamp, swing_batch

