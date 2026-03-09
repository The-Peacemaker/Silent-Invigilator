import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/modern_theme.dart';
import '../services/invigilator_service.dart';
import 'login_screen.dart';
import 'home_screen.dart';

class AdminDashboardScreen extends StatefulWidget {
  final InvigilatorService service;
  const AdminDashboardScreen({super.key, required this.service});

  @override
  State<AdminDashboardScreen> createState() => _AdminDashboardScreenState();
}

class _AdminDashboardScreenState extends State<AdminDashboardScreen> {
  Map<String, dynamic>? _stats;
  List<UserEntry>? _users;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    setState(() => _isLoading = true);
    final stats = await widget.service.fetchAdminStats();
    final users = await widget.service.fetchUsers();

    if (mounted) {
      setState(() {
        _stats = stats;
        _users = users;
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
          'Admin Dashboard',
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
                    _buildOverviewCards(),
                    const SizedBox(height: 24),
                    _buildChartsSection(),
                    const SizedBox(height: 24),
                    _buildUserManagement(),
                    const SizedBox(height: 32),
                  ],
                ),
              ),
            ),
    );
  }

  Widget _buildOverviewCards() {
    final tAlerts = _stats!['total_alerts'] ?? 0;
    final cAlerts = _stats!['critical_alerts'] ?? 0;
    final wAlerts = _stats!['warning_alerts'] ?? 0;
    final tUsers = _stats!['total_users'] ?? 0;

    return GridView.count(
      crossAxisCount: 2,
      crossAxisSpacing: 16,
      mainAxisSpacing: 16,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      childAspectRatio: 1.3,
      children: [
        _buildStatCard(
          'TOTAL ALERTS',
          tAlerts.toString(),
          Icons.notifications_active,
          ModernColors.statusInfo,
        ),
        _buildStatCard(
          'CRITICAL',
          cAlerts.toString(),
          Icons.warning_amber_rounded,
          ModernColors.statusDanger,
        ),
        _buildStatCard(
          'WARNINGS',
          wAlerts.toString(),
          Icons.error_outline,
          ModernColors.statusWarn,
        ),
        _buildStatCard(
          'USERS',
          tUsers.toString(),
          Icons.people_outline,
          ModernColors.accentPurple,
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
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icon, color: color, size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    color: ModernColors.textSecondary,
                    fontWeight: FontWeight.bold,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const Spacer(),
          Text(
            value,
            style: GoogleFonts.outfit(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: ModernColors.textPrimary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChartsSection() {
    List<dynamic> dist = _stats!['type_distribution'] ?? [];

    return Container(
      decoration: ModernTheme.glassDecoration(),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Alert Distribution',
            style: GoogleFonts.outfit(
              fontSize: 18,
              fontWeight: FontWeight.w600,
              color: ModernColors.textPrimary,
            ),
          ),
          const SizedBox(height: 24),
          SizedBox(
            height: 200,
            child: dist.isEmpty
                ? const Center(child: Text('No data'))
                : PieChart(
                    PieChartData(
                      sectionsSpace: 2,
                      centerSpaceRadius: 40,
                      sections: dist.asMap().entries.map((e) {
                        final i = e.key;
                        final item = e.value;
                        final colors = [
                          ModernColors.statusDanger,
                          ModernColors.statusWarn,
                          ModernColors.accentCyan,
                          ModernColors.accentPurple,
                        ];
                        return PieChartSectionData(
                          color: colors[i % colors.length],
                          value: (item['count'] as num).toDouble(),
                          title: '${item['count']}',
                          radius: 50,
                          titleStyle: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        );
                      }).toList(),
                    ),
                  ),
          ),
          const SizedBox(height: 16),
          // Legend
          ...dist.asMap().entries.map((e) {
            final i = e.key;
            final item = e.value;
            final colors = [
              ModernColors.statusDanger,
              ModernColors.statusWarn,
              ModernColors.accentCyan,
              ModernColors.accentPurple,
            ];
            return Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                children: [
                  Container(
                    width: 12,
                    height: 12,
                    decoration: BoxDecoration(
                      color: colors[i % colors.length],
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      item['type'],
                      style: GoogleFonts.inter(
                        fontSize: 12,
                        color: ModernColors.textSecondary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }

  Widget _buildUserManagement() {
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
                'System Users',
                style: GoogleFonts.outfit(
                  fontSize: 18,
                  fontWeight: FontWeight.w600,
                  color: ModernColors.textPrimary,
                ),
              ),
              ElevatedButton.icon(
                onPressed: () {},
                icon: const Icon(Icons.add, size: 16),
                label: const Text('Add User'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: ModernColors.glassBg,
                  foregroundColor: ModernColors.accentCyan,
                  side: const BorderSide(color: ModernColors.glassBorder),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          if (_users == null || _users!.isEmpty)
            const Text('No users found.')
          else
            ListView.separated(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: _users!.length,
              separatorBuilder: (_, __) =>
                  const Divider(color: ModernColors.glassBorder, height: 1),
              itemBuilder: (context, index) {
                final u = _users![index];
                return ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: CircleAvatar(
                    backgroundColor: u.role == 'admin'
                        ? ModernColors.accentPurple.withOpacity(0.2)
                        : ModernColors.accentCyan.withOpacity(0.2),
                    child: Icon(
                      u.role == 'admin' ? Icons.shield : Icons.person,
                      color: u.role == 'admin'
                          ? ModernColors.accentPurple
                          : ModernColors.accentCyan,
                      size: 20,
                    ),
                  ),
                  title: Text(
                    u.fullName,
                    style: GoogleFonts.inter(
                      fontWeight: FontWeight.w600,
                      color: ModernColors.textPrimary,
                    ),
                  ),
                  subtitle: Text(
                    '@${u.username} • ${u.role}',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      color: ModernColors.textSecondary,
                    ),
                  ),
                  trailing: IconButton(
                    icon: const Icon(
                      Icons.delete_outline,
                      color: ModernColors.statusDanger,
                      size: 20,
                    ),
                    onPressed: () {},
                  ),
                );
              },
            ),
        ],
      ),
    );
  }
}
