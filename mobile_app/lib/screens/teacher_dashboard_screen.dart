import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/modern_theme.dart';
import '../services/invigilator_service.dart';
import 'login_screen.dart';
import 'home_screen.dart'; // We'll update this to be the monitor screen.

class TeacherDashboardScreen extends StatefulWidget {
  final InvigilatorService service;
  const TeacherDashboardScreen({super.key, required this.service});

  @override
  State<TeacherDashboardScreen> createState() => _TeacherDashboardScreenState();
}

class _TeacherDashboardScreenState extends State<TeacherDashboardScreen> {
  Map<String, dynamic>? _stats;
  List<LogEntry>? _alerts;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final stats = await widget.service.fetchTeacherStats();
    final alerts = await widget.service.fetchAlerts();

    if (mounted) {
      setState(() {
        _stats = stats;
        _alerts = alerts;
        _isLoading = false;
      });
    }
  }

  void _logout() {
    widget.service.dispose();
    Navigator.of(
      context,
    ).pushReplacement(MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  void _openMonitor() {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => HomeScreen(serverUrl: widget.service.baseUrl),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Teacher Dashboard',
          style: GoogleFonts.outfit(fontWeight: FontWeight.bold),
        ),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), onPressed: _loadData),
          IconButton(icon: const Icon(Icons.logout), onPressed: _logout),
          const SizedBox(width: 8),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openMonitor,
        backgroundColor: ModernColors.accentCyan,
        icon: const Icon(Icons.videocam, color: ModernColors.bgPrimary),
        label: Text(
          'LIVE MONITOR',
          style: GoogleFonts.jetBrainsMono(
            fontWeight: FontWeight.bold,
            color: ModernColors.bgPrimary,
          ),
        ),
      ),
      body: _isLoading
          ? const Center(
              child: CircularProgressIndicator(color: ModernColors.accentCyan),
            )
          : RefreshIndicator(
              onRefresh: _loadData,
              color: ModernColors.accentCyan,
              backgroundColor: ModernColors.bgSecondary,
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _buildWelcomeCard(),
                    const SizedBox(height: 24),
                    _buildOverviewCards(),
                    const SizedBox(height: 24),
                    _buildRecentAlerts(),
                    const SizedBox(height: 80), // Space for FAB
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildWelcomeCard() {
    return Container(
      decoration: ModernTheme.glassDecoration(),
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Active Session Monitoring',
            style: GoogleFonts.outfit(
              fontSize: 24,
              fontWeight: FontWeight.bold,
              foreground: Paint()..shader = ModernTheme.linearGradientShader,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Keep an eye on the latest AI surveillance alerts. Tap Live Monitor to view the real-time camera feed.',
            style: GoogleFonts.inter(
              color: ModernColors.textSecondary,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildOverviewCards() {
    final tAlerts = _stats!['total_alerts'] ?? 0;
    final cAlerts = _stats!['critical_alerts'] ?? 0;
    final wAlerts = _stats!['warning_alerts'] ?? 0;

    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            'TOTAL ALERTS',
            tAlerts.toString(),
            Icons.notifications,
            ModernColors.statusInfo,
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildStatCard(
            'CRITICAL',
            cAlerts.toString(),
            Icons.warning,
            ModernColors.statusDanger,
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildStatCard(
            'WARNINGS',
            wAlerts.toString(),
            Icons.error,
            ModernColors.statusWarn,
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard(
    String title,
    String value,
    IconData icon,
    Color color,
  ) {
    return Container(
      decoration: ModernTheme.glassDecoration(),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Icon(icon, color: color, size: 28),
          const SizedBox(height: 12),
          Text(
            value,
            style: GoogleFonts.outfit(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: ModernColors.textPrimary,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            title,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 10,
              color: ModernColors.textSecondary,
              fontWeight: FontWeight.bold,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildRecentAlerts() {
    return Container(
      decoration: ModernTheme.glassDecoration(),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Recent Detections',
                style: GoogleFonts.outfit(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: ModernColors.textPrimary,
                ),
              ),
              Text(
                'LIVE',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                  color: ModernColors.statusDanger,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_alerts == null || _alerts!.isEmpty)
            const Text('No recent alerts.')
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _alerts!.length,
              separatorBuilder: (_, __) =>
                  const Divider(color: ModernColors.glassBorder, height: 1),
              itemBuilder: (context, index) {
                final a = _alerts![index];
                final isCritical = a.riskScore >= 70;
                final isWarning = a.riskScore >= 40 && a.riskScore < 70;

                final color = isCritical
                    ? ModernColors.statusDanger
                    : (isWarning
                          ? ModernColors.statusWarn
                          : ModernColors.statusInfo);
                final icon = isCritical
                    ? Icons.cancel
                    : (isWarning ? Icons.error : Icons.info);

                return ListTile(
                  contentPadding: const EdgeInsets.symmetric(vertical: 8),
                  leading: Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Icon(icon, color: color, size: 20),
                  ),
                  title: Text(
                    a.eventType,
                    style: GoogleFonts.inter(
                      fontWeight: FontWeight.w600,
                      color: ModernColors.textPrimary,
                      fontSize: 14,
                    ),
                  ),
                  subtitle: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const SizedBox(height: 4),
                      Text(
                        a.description,
                        style: GoogleFonts.inter(
                          fontSize: 13,
                          color: ModernColors.textSecondary,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        a.timestamp,
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 10,
                          color: ModernColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                  trailing: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: color.withOpacity(0.1),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: color.withOpacity(0.3)),
                    ),
                    child: Text(
                      '${a.riskScore}',
                      style: GoogleFonts.jetBrainsMono(
                        color: color,
                        fontWeight: FontWeight.bold,
                        fontSize: 13,
                      ),
                    ),
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
