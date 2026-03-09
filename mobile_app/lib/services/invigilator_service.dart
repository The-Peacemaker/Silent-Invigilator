import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

/// Data model for system status from /status API
class InvigilatorStatus {
  final int riskScore;
  final bool faceDetected;
  final bool phoneDetected;
  final String headPose;
  final String gaze;
  final double yaw;
  final double pitch;
  final List<String> detections;
  final int persons;
  final int audioLevel;

  InvigilatorStatus({
    required this.riskScore,
    required this.faceDetected,
    required this.phoneDetected,
    required this.headPose,
    required this.gaze,
    required this.yaw,
    required this.pitch,
    required this.detections,
    required this.persons,
    required this.audioLevel,
  });

  factory InvigilatorStatus.empty() => InvigilatorStatus(
    riskScore: 0,
    faceDetected: false,
    phoneDetected: false,
    headPose: 'Center',
    gaze: 'Center',
    yaw: 0,
    pitch: 0,
    detections: [],
    persons: 0,
    audioLevel: 0,
  );

  factory InvigilatorStatus.fromJson(Map<String, dynamic> json) {
    return InvigilatorStatus(
      riskScore: (json['risk_score'] ?? 0).toInt(),
      faceDetected: json['face_detected'] ?? false,
      phoneDetected: json['phone_detected'] ?? false,
      headPose: json['head_pose'] ?? 'Center',
      gaze: json['gaze'] ?? 'Center',
      yaw: (json['yaw'] ?? 0).toDouble(),
      pitch: (json['pitch'] ?? 0).toDouble(),
      detections:
          (json['detections'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      persons: (json['persons'] ?? 0).toInt(),
      audioLevel: (json['audio_level'] ?? 0).toInt(),
    );
  }

  String get riskLabel {
    if (riskScore < 30) return 'LOW RISK';
    if (riskScore < 70) return 'SUSPICIOUS';
    return 'HIGH RISK';
  }

  String get behavioralState {
    if (riskScore >= 70 || phoneDetected) return '⚠ SUSPICIOUS BEHAVIOR';
    if (detections.any(
      (d) => d.toLowerCase().contains('down') || d.toLowerCase().contains('up'),
    )) {
      return '↕ Looking Away';
    }
    if (headPose != 'Center' || gaze != 'Center') return '↔ Looking Away';
    return '✓ Focused';
  }
}

/// Alert log entry
class AlertEntry {
  final DateTime timestamp;
  final String message;
  final String type; // 'warn', 'danger', 'info'

  AlertEntry({
    required this.timestamp,
    required this.message,
    required this.type,
  });
}

/// Database log entry from /dashboard API
class LogEntry {
  final int id;
  final String timestamp;
  final int riskScore;
  final String eventType;
  final String description;

  LogEntry({
    required this.id,
    required this.timestamp,
    required this.riskScore,
    required this.eventType,
    required this.description,
  });

  factory LogEntry.fromJson(Map<String, dynamic> json) {
    return LogEntry(
      id: json['id'] ?? 0,
      timestamp: json['timestamp'] ?? '',
      riskScore: (json['risk_score'] ?? 0).toInt(),
      eventType: json['event_type'] ?? '',
      description: json['description'] ?? '',
    );
  }
}

class UserEntry {
  final int id;
  final String username;
  final String role;
  final String fullName;
  final String createdAt;

  UserEntry({
    required this.id,
    required this.username,
    required this.role,
    required this.fullName,
    required this.createdAt,
  });

  factory UserEntry.fromJson(Map<String, dynamic> json) {
    return UserEntry(
      id: json['id'] ?? 0,
      username: json['username'] ?? '',
      role: json['role'] ?? '',
      fullName: json['full_name'] ?? '',
      createdAt: json['created_at'] ?? '',
    );
  }
}

/// Service to poll the Flask backend — with automatic DEMO FALLBACK
class InvigilatorService {
  String baseUrl;
  Timer? _pollTimer;
  bool _isPolling = false;

  final StreamController<InvigilatorStatus> _statusController =
      StreamController<InvigilatorStatus>.broadcast();
  final StreamController<bool> _connectionController =
      StreamController<bool>.broadcast();
  final List<AlertEntry> alertLog = [];
  int sessionAlertCount = 0;
  DateTime _lastAlertTime = DateTime(2000);

  Stream<InvigilatorStatus> get statusStream => _statusController.stream;
  Stream<bool> get connectionStream => _connectionController.stream;

  InvigilatorStatus _lastStatus = InvigilatorStatus.empty();
  InvigilatorStatus get lastStatus => _lastStatus;
  bool _connected = false;
  bool get isConnected => _connected;

  // Auth state
  String? currentRole;
  String? currentUsername;

  // ── DEMO MODE ──────────────────────────────────────────
  bool _demoMode =
      true; // Defaulting to demo mode initially if backend not set up
  bool get isDemoMode => _demoMode;
  int _failCount = 0;
  DateTime? _demoStart;
  final _rng = Random();

  // Demo script: (durationSecs, pose, gaze, risk, phone, detections)
  static const List<List<dynamic>> _demoScript = [
    [12, 'Center', 'Center', 5, false, <String>[]],
    [3, 'Center', 'Center', 15, false, <String>[]],
    [
      8,
      'Right',
      'Right',
      35,
      false,
      ['Head Turn (Right)'],
    ],
    [3, 'Center', 'Center', 20, false, <String>[]],
    [10, 'Center', 'Center', 3, false, <String>[]],
    [3, 'Center', 'Center', 25, false, <String>[]],
    [
      8,
      'Down',
      'Center',
      55,
      false,
      ['Looking Down'],
    ],
    [3, 'Center', 'Center', 15, false, <String>[]],
    [8, 'Center', 'Center', 5, false, <String>[]],
    [3, 'Center', 'Left', 40, false, <String>[]],
    [
      10,
      'Center',
      'Center',
      85,
      true,
      ['PHONE DETECTED'],
    ],
    [3, 'Center', 'Center', 30, false, <String>[]],
    [12, 'Center', 'Center', 8, false, <String>[]],
    [
      5,
      'Left',
      'Left',
      30,
      false,
      ['Head Turn (Left)'],
    ],
    [3, 'Center', 'Center', 10, false, <String>[]],
    [10, 'Center', 'Center', 2, false, <String>[]],
  ];

  static int get _totalScriptTime =>
      _demoScript.fold<int>(0, (sum, s) => sum + (s[0] as int));

  InvigilatorService({this.baseUrl = 'http://10.0.2.2:5000'});

  // API METHODS ----------------------------------------------------

  /// Login to the Flask backend
  Future<bool> login(String username, String password, String role) async {
    try {
      // Always allow demo logins right away
      if ((username == 'admin' && password == 'admin123') ||
          (username == 'teacher' && password == 'teacher123') ||
          (username == 'admin' && password == 'admin')) {
        currentUsername = username;
        currentRole = role; // Store the selected role
        return true;
      }

      final response = await http
          .post(
            Uri.parse('$baseUrl/login'),
            body: {'username': username, 'password': password, 'role': role},
          )
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 302 || response.statusCode == 200) {
        currentUsername = username;
        currentRole = role;
        return true;
      }
      return false;
    } catch (e) {
      // Fallback for demo
      if (username == 'admin' || username == 'teacher') {
        currentUsername = username;
        currentRole = role;
        return true;
      }
      return false;
    }
  }

  Future<Map<String, dynamic>> fetchAdminStats() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/admin/stats'))
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      // Generate demo data
    }
    return {
      'total_alerts': 124,
      'critical_alerts': 18,
      'warning_alerts': 45,
      'total_users': 5,
      'type_distribution': [
        {'type': 'Suspicious Behavior', 'count': 82},
        {'type': 'PROHIBITED OBJECT (PHONE)', 'count': 24},
        {'type': 'COLLUSION (PROXIMITY)', 'count': 12},
        {'type': 'AUDIO VIOLATION', 'count': 6},
      ],
      'hourly_trend': [
        {'hour': '08', 'count': 12, 'avg_score': 45.2},
        {'hour': '09', 'count': 25, 'avg_score': 68.4},
        {'hour': '10', 'count': 15, 'avg_score': 55.1},
        {'hour': '11', 'count': 8, 'avg_score': 32.5},
      ],
    };
  }

  Future<List<UserEntry>> fetchUsers() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/admin/users'))
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        Iterable l = json.decode(response.body);
        return List<UserEntry>.from(
          l.map((model) => UserEntry.fromJson(model)),
        );
      }
    } catch (e) {
      // Ignore
    }
    return [
      UserEntry(
        id: 1,
        username: 'admin',
        role: 'admin',
        fullName: 'Administrator',
        createdAt: '2026-03-01',
      ),
      UserEntry(
        id: 2,
        username: 'sarah',
        role: 'teacher',
        fullName: 'Dr. Sarah Mitchell',
        createdAt: '2026-03-02',
      ),
      UserEntry(
        id: 3,
        username: 'james',
        role: 'teacher',
        fullName: 'Prof. James Wilson',
        createdAt: '2026-03-02',
      ),
    ];
  }

  Future<Map<String, dynamic>> fetchTeacherStats() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/api/stats'))
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        return json.decode(response.body);
      }
    } catch (e) {
      // Ignore
    }
    return {
      'total_alerts': 45,
      'critical_alerts': 8,
      'warning_alerts': 15,
      'type_distribution': [
        {'type': 'Suspicious Behavior', 'count': 30},
        {'type': 'PROHIBITED OBJECT (PHONE)', 'count': 5},
      ],
      'hourly_trend': [],
    };
  }

  Future<List<LogEntry>> fetchAlerts() async {
    try {
      final response = await http
          .get(Uri.parse('$baseUrl/api/alerts?limit=20'))
          .timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        Iterable l = json.decode(response.body);
        return List<LogEntry>.from(l.map((model) => LogEntry.fromJson(model)));
      }
    } catch (e) {
      // Ignore
    }
    return [
      LogEntry(
        id: 1,
        timestamp: '2026-03-03 09:28:44',
        riskScore: 82,
        eventType: 'AUDIO VIOLATION',
        description: 'High decibel verbal exchange',
      ),
      LogEntry(
        id: 2,
        timestamp: '2026-03-03 09:25:30',
        riskScore: 98,
        eventType: 'PROHIBITED OBJECT (PHONE)',
        description: 'CRITICAL: PHONE DETECTED',
      ),
      LogEntry(
        id: 3,
        timestamp: '2026-03-03 09:20:05',
        riskScore: 64,
        eventType: 'Suspicious Behavior',
        description: 'Continuous hallway scanning pattern',
      ),
      LogEntry(
        id: 4,
        timestamp: '2026-03-03 09:12:44',
        riskScore: 42,
        eventType: 'Suspicious Behavior',
        description: 'Repeated hand movements under desk',
      ),
    ];
  }

  // POLLING METHODS ----------------------------------------------------

  void startPolling({Duration interval = const Duration(seconds: 1)}) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(interval, (_) => _poll());
    _poll(); // immediate first poll
  }

  void stopPolling() {
    _pollTimer?.cancel();
    _pollTimer = null;
  }

  Future<void> _poll() async {
    if (_isPolling) return;
    _isPolling = true;

    // If in demo mode, generate fake data
    if (_demoMode) {
      _generateDemoStatus();
      _isPolling = false;
      return;
    }

    try {
      final response = await http
          .get(Uri.parse('$baseUrl/status'))
          .timeout(const Duration(seconds: 3));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        _lastStatus = InvigilatorStatus.fromJson(data);
        _statusController.add(_lastStatus);

        if (!_connected) {
          _connected = true;
          _connectionController.add(true);
        }

        _failCount = 0; // reset fail counter on success
        _processAlerts(_lastStatus);
      }
    } catch (e) {
      _failCount++;
      // After 3 failed attempts, automatically switch to demo mode
      if (_failCount >= 3 && !_demoMode) {
        _demoMode = true;
        _demoStart = DateTime.now();
        _connected = true; // pretend connected for demo
        _connectionController.add(true);
        print('[DEMO] Server unreachable — switching to local demo mode');
      } else if (!_demoMode) {
        if (_connected) {
          _connected = false;
          _connectionController.add(false);
        }
      }
    } finally {
      _isPolling = false;
    }
  }

  /// Generate simulated detection data based on the demo script timeline
  void _generateDemoStatus() {
    _demoStart ??= DateTime.now();
    final elapsed = DateTime.now().difference(_demoStart!).inSeconds;
    final loopPos = elapsed % _totalScriptTime;

    // Find current script entry
    int cumulative = 0;
    List<dynamic> current = _demoScript[0];
    for (final entry in _demoScript) {
      cumulative += entry[0] as int;
      if (loopPos < cumulative) {
        current = entry;
        break;
      }
    }

    final pose = current[1] as String;
    final gaze = current[2] as String;
    final baseRisk = current[3] as int;
    final phone = current[4] as bool;
    final dets = List<String>.from(current[5] as List);

    // Add natural jitter
    final jitter = _rng.nextInt(7) - 3;
    final risk = (baseRisk + jitter).clamp(0, 100);

    // Simulate yaw/pitch
    double yaw, pitch;
    if (pose == 'Right') {
      yaw = 30 + _rng.nextDouble() * 6 - 3;
      pitch = _rng.nextDouble() * 10 - 5;
    } else if (pose == 'Left') {
      yaw = -30 + _rng.nextDouble() * 6 - 3;
      pitch = _rng.nextDouble() * 10 - 5;
    } else if (pose == 'Down') {
      yaw = _rng.nextDouble() * 10 - 5;
      pitch = 22 + _rng.nextDouble() * 6 - 3;
    } else {
      yaw = _rng.nextDouble() * 16 - 8;
      pitch = _rng.nextDouble() * 10 - 5;
    }

    _lastStatus = InvigilatorStatus(
      riskScore: risk,
      faceDetected: true,
      phoneDetected: phone,
      headPose: pose,
      gaze: gaze,
      yaw: double.parse(yaw.toStringAsFixed(1)),
      pitch: double.parse(pitch.toStringAsFixed(1)),
      detections: dets,
      persons: 1,
      audioLevel: _rng.nextInt(15) + 30,
    );

    _statusController.add(_lastStatus);
    _processAlerts(_lastStatus);
  }

  void _processAlerts(InvigilatorStatus status) {
    final now = DateTime.now();
    if (now.difference(_lastAlertTime).inMilliseconds < 2500) return;

    if (!status.faceDetected) {
      _addAlert('⚠ No face detected — student may be absent', 'danger');
    }
    if (status.phoneDetected) {
      _addAlert('🚨 Mobile phone detected in frame!', 'danger');
    }
    if (status.riskScore >= 70) {
      final reasons = status.detections.take(2).join(' · ');
      _addAlert(
        'High risk detected — ${reasons.isNotEmpty ? reasons : "High Risk Behavior"}',
        'danger',
      );
    }
    for (final det in status.detections) {
      final dl = det.toLowerCase();
      if (dl.contains('talking') || dl.contains('mouth')) {
        _addAlert('🗣 Talking detected', 'warn');
      }
      if (dl.contains('proximity')) {
        _addAlert('👥 Proximity alert — students too close', 'warn');
      }
      if (dl.contains('looking down')) {
        _addAlert('👇 Student looking down', 'warn');
      }
    }
  }

  void _addAlert(String msg, String type) {
    _lastAlertTime = DateTime.now();
    sessionAlertCount++;
    alertLog.insert(
      0,
      AlertEntry(timestamp: DateTime.now(), message: msg, type: type),
    );
    if (alertLog.length > 50) {
      alertLog.removeLast();
    }
  }

  void clearAlerts() {
    alertLog.clear();
    sessionAlertCount = 0;
  }

  String get videoFeedUrl => '$baseUrl/video_feed';

  void dispose() {
    stopPolling();
    _statusController.close();
    _connectionController.close();
  }
}
