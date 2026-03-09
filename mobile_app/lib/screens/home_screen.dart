import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/modern_theme.dart';
import '../services/invigilator_service.dart';

class HomeScreen extends StatefulWidget {
  final String serverUrl;
  const HomeScreen({super.key, required this.serverUrl});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late InvigilatorService _service;

  @override
  void initState() {
    super.initState();
    _service = InvigilatorService(baseUrl: widget.serverUrl);
    _service.startPolling();
  }

  @override
  void dispose() {
    _service.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        title: Row(
          children: [
            const Icon(
              Icons.emergency_recording,
              color: ModernColors.statusDanger,
              size: 20,
            ),
            const SizedBox(width: 8),
            Text(
              'LIVE FEED',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: ModernColors.statusDanger,
              ),
            ),
          ],
        ),
      ),
      body: Stack(
        children: [
          // Background Color
          Container(color: ModernColors.bgPrimary),

          // The MJPEG Feed (or Placeholder if Demo)
          Positioned.fill(
            child: _service.isDemoMode
                ? Container(
                    decoration: BoxDecoration(
                      gradient: RadialGradient(
                        colors: [
                          ModernColors.bgSecondary,
                          ModernColors.bgPrimary,
                        ],
                        radius: 1.5,
                      ),
                    ),
                    child: Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            Icons.videocam_off_outlined,
                            size: 64,
                            color: ModernColors.textMuted,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            'DEMO MODE: No Camera Connected',
                            style: GoogleFonts.inter(
                              color: ModernColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                : Image.network(
                    _service.videoFeedUrl,
                    fit: BoxFit.cover,
                    gaplessPlayback: true,
                    errorBuilder: (context, error, stackTrace) {
                      return Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            const Icon(
                              Icons.broken_image_outlined,
                              size: 64,
                              color: ModernColors.textMuted,
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Video Feed Offline',
                              style: GoogleFonts.inter(
                                color: ModernColors.textSecondary,
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),

          // Live Data Overlay
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Top HUD
                  StreamBuilder<InvigilatorStatus>(
                    stream: _service.statusStream,
                    builder: (context, snapshot) {
                      final status = snapshot.data ?? InvigilatorStatus.empty();
                      return _buildTopHud(status);
                    },
                  ),

                  const Spacer(),

                  // Bottom Detection Log Overlay
                  StreamBuilder<InvigilatorStatus>(
                    stream: _service.statusStream,
                    builder: (context, snapshot) {
                      final status = snapshot.data ?? InvigilatorStatus.empty();
                      return _buildBottomHud(status);
                    },
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTopHud(InvigilatorStatus status) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // AI Metrics Panel
        Expanded(
          child: Container(
            decoration: ModernTheme.glassDecoration(),
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'AI SENSOR METRICS',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    color: ModernColors.accentCyan,
                  ),
                ),
                const SizedBox(height: 8),
                _buildMetricRow(
                  'FACE',
                  status.faceDetected ? 'DETECTED' : 'NONE',
                  status.faceDetected
                      ? ModernColors.statusSafe
                      : ModernColors.textMuted,
                ),
                _buildMetricRow(
                  'POSE',
                  status.headPose,
                  status.headPose == 'Center'
                      ? ModernColors.statusSafe
                      : ModernColors.statusWarn,
                ),
                _buildMetricRow(
                  'GAZE',
                  status.gaze,
                  status.gaze == 'Center'
                      ? ModernColors.statusSafe
                      : ModernColors.statusWarn,
                ),
                _buildMetricRow(
                  'AUDIO',
                  '${status.audioLevel} dB',
                  status.audioLevel < 50
                      ? ModernColors.statusSafe
                      : ModernColors.statusDanger,
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: 12),
        // Risk & Score Panel
        Container(
          width: 140,
          decoration: ModernTheme.glassDecoration(),
          padding: const EdgeInsets.all(12),
          child: Column(
            children: [
              Text(
                'ANOMALY SVR',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 10,
                  color: ModernColors.textSecondary,
                ),
              ),
              const SizedBox(height: 8),
              Stack(
                alignment: Alignment.center,
                children: [
                  SizedBox(
                    height: 60,
                    width: 60,
                    child: CircularProgressIndicator(
                      value: status.riskScore / 100,
                      strokeWidth: 6,
                      color: status.riskScore > 70
                          ? ModernColors.statusDanger
                          : (status.riskScore > 30
                                ? ModernColors.statusWarn
                                : ModernColors.statusSafe),
                      backgroundColor: ModernColors.bgPrimary,
                    ),
                  ),
                  Text(
                    '${status.riskScore}',
                    style: GoogleFonts.outfit(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                status.behavioralState,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.bold,
                  color: status.riskScore > 70
                      ? ModernColors.statusDanger
                      : (status.riskScore > 30
                            ? ModernColors.statusWarn
                            : ModernColors.statusSafe),
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMetricRow(String label, String value, Color valueColor) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              color: ModernColors.textSecondary,
            ),
          ),
          Text(
            value,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              fontWeight: FontWeight.bold,
              color: valueColor,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBottomHud(InvigilatorStatus status) {
    if (status.detections.isEmpty && !status.phoneDetected) {
      return const SizedBox.shrink(); // Hide if nothing detected
    }

    return Container(
      decoration: BoxDecoration(
        color: ModernColors.bgPrimary.withOpacity(0.85),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: ModernColors.statusDanger.withOpacity(0.5)),
      ),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.warning,
                color: ModernColors.statusDanger,
                size: 16,
              ),
              const SizedBox(width: 8),
              Text(
                'ACTIVE DETECTIONS',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: ModernColors.statusDanger,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          if (status.phoneDetected)
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                '► PROHIBITED OBJECT: PHONE',
                style: GoogleFonts.inter(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ...status.detections.map(
            (d) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Text(
                '► Anomaly: $d',
                style: GoogleFonts.inter(color: ModernColors.statusWarn),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
