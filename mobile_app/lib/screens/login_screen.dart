import 'dart:math';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/modern_theme.dart';
import '../services/invigilator_service.dart';
import 'home_screen.dart'; // We will update this later to be monitor_screen etc.
import 'admin_dashboard_screen.dart';
import 'teacher_dashboard_screen.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _serverController = TextEditingController(text: 'http://10.0.2.2:5000');

  String _selectedRole = 'teacher';
  bool _isLoading = false;
  String? _error;
  late AnimationController _shakeController;

  @override
  void initState() {
    super.initState();
    _shakeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _serverController.dispose();
    _shakeController.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    final username = _usernameController.text.trim();
    final password = _passwordController.text.trim();
    final server = _serverController.text.trim();

    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = 'All fields are required.');
      _shakeController.forward(from: 0);
      return;
    }

    setState(() {
      _isLoading = true;
      _error = null;
    });

    final service = InvigilatorService(baseUrl: server);
    final success = await service.login(username, password, _selectedRole);

    if (!mounted) return;

    if (success) {
      if (_selectedRole == 'admin') {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => AdminDashboardScreen(service: service),
          ),
        );
      } else {
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => TeacherDashboardScreen(service: service),
          ),
        );
      }
    } else {
      setState(() {
        _isLoading = false;
        _error = 'Invalid Credentials. Access Denied.';
      });
      _shakeController.forward(from: 0);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // Background Elements
          Container(
            width: double.infinity,
            height: double.infinity,
            decoration: const BoxDecoration(color: ModernColors.bgPrimary),
          ),
          // Glow effects
          Positioned(
            top: -100,
            left: -100,
            child: Container(
              width: 400,
              height: 400,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    ModernColors.accentCyan.withOpacity(0.15),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          Positioned(
            bottom: -100,
            right: -100,
            child: Container(
              width: 400,
              height: 400,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [
                    ModernColors.accentPurple.withOpacity(0.15),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),

          Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: AnimatedBuilder(
                animation: _shakeController,
                builder: (context, child) {
                  final shakeOffset =
                      sin(_shakeController.value * 3 * 3.14159) *
                      8 *
                      (1 - _shakeController.value);
                  return Transform.translate(
                    offset: Offset(shakeOffset, 0),
                    child: child,
                  );
                },
                child: Container(
                  width: 380,
                  padding: const EdgeInsets.all(32),
                  decoration: ModernTheme.glassDecoration(borderRadius: 24),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Logo/Icon
                      Container(
                        padding: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: ModernColors.glassBg,
                          shape: BoxShape.circle,
                          border: Border.all(color: ModernColors.glassBorder),
                        ),
                        child: const Icon(
                          Icons.visibility_outlined,
                          size: 48,
                          color: ModernColors.accentCyan,
                        ),
                      ),
                      const SizedBox(height: 24),

                      Text(
                        'System Login',
                        style: GoogleFonts.outfit(
                          fontSize: 32,
                          fontWeight: FontWeight.bold,
                          foreground: Paint()
                            ..shader = ModernTheme.linearGradientShader,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Authenticate to access surveillance',
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          color: ModernColors.textSecondary,
                        ),
                      ),
                      const SizedBox(height: 32),

                      if (_error != null)
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          margin: const EdgeInsets.only(bottom: 24),
                          decoration: BoxDecoration(
                            color: ModernColors.statusDanger.withOpacity(0.1),
                            border: Border.all(
                              color: ModernColors.statusDanger.withOpacity(0.3),
                            ),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.error_outline,
                                color: ModernColors.statusDanger,
                                size: 20,
                              ),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  _error!,
                                  style: GoogleFonts.inter(
                                    color: ModernColors.statusDanger,
                                    fontSize: 13,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),

                      _buildField(
                        label: 'SERVER URL',
                        controller: _serverController,
                        hint: 'http://10.0.2.2:5000',
                        icon: Icons.dns_outlined,
                      ),
                      const SizedBox(height: 20),

                      _buildField(
                        label: 'USERNAME',
                        controller: _usernameController,
                        hint: 'admin',
                        icon: Icons.person_outline,
                      ),
                      const SizedBox(height: 20),

                      _buildField(
                        label: 'PASSWORD',
                        controller: _passwordController,
                        hint: '••••••••',
                        isPassword: true,
                        icon: Icons.lock_outline,
                      ),
                      const SizedBox(height: 20),

                      // Role Selector
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'ACCESS ROLE',
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 11,
                              fontWeight: FontWeight.bold,
                              color: ModernColors.accentCyan,
                              letterSpacing: 1,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            decoration: BoxDecoration(
                              color: const Color(0x330A0A1A),
                              border: Border.all(
                                color: ModernColors.glassBorder,
                              ),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: DropdownButtonHideUnderline(
                              child: DropdownButton<String>(
                                value: _selectedRole,
                                isExpanded: true,
                                dropdownColor: ModernColors.bgTertiary,
                                icon: const Icon(
                                  Icons.keyboard_arrow_down,
                                  color: ModernColors.textSecondary,
                                ),
                                style: GoogleFonts.inter(
                                  color: ModernColors.textPrimary,
                                  fontSize: 16,
                                ),
                                items: const [
                                  DropdownMenuItem(
                                    value: 'admin',
                                    child: Text('Administrator'),
                                  ),
                                  DropdownMenuItem(
                                    value: 'teacher',
                                    child: Text('Teacher / Invigilator'),
                                  ),
                                ],
                                onChanged: (val) {
                                  if (val != null)
                                    setState(() => _selectedRole = val);
                                },
                              ),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 32),

                      SizedBox(
                        width: double.infinity,
                        height: 50,
                        child: ElevatedButton(
                          onPressed: _isLoading ? null : _login,
                          style: ElevatedButton.styleFrom(
                            padding: EdgeInsets.zero,
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                            backgroundColor: Colors.transparent,
                            shadowColor: Colors.transparent,
                          ),
                          child: Ink(
                            decoration: ModernTheme.primaryButtonDecoration(),
                            child: Container(
                              alignment: Alignment.center,
                              child: _isLoading
                                  ? const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2,
                                      ),
                                    )
                                  : Text(
                                      'AUTHORIZE START',
                                      style: GoogleFonts.jetBrainsMono(
                                        color: Colors.white,
                                        fontWeight: FontWeight.bold,
                                        letterSpacing: 1,
                                      ),
                                    ),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildField({
    required String label,
    required TextEditingController controller,
    required String hint,
    bool isPassword = false,
    required IconData icon,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: GoogleFonts.jetBrainsMono(
            fontSize: 11,
            fontWeight: FontWeight.bold,
            color: ModernColors.accentCyan,
            letterSpacing: 1,
          ),
        ),
        const SizedBox(height: 8),
        Container(
          decoration: BoxDecoration(
            color: const Color(0x330A0A1A),
            border: Border.all(color: ModernColors.glassBorder),
            borderRadius: BorderRadius.circular(8),
          ),
          child: TextField(
            controller: controller,
            obscureText: isPassword,
            style: GoogleFonts.inter(
              fontSize: 16,
              color: ModernColors.textPrimary,
            ),
            decoration: InputDecoration(
              hintText: hint,
              hintStyle: GoogleFonts.inter(
                fontSize: 16,
                color: ModernColors.textMuted,
              ),
              prefixIcon: Icon(
                icon,
                size: 20,
                color: ModernColors.textSecondary,
              ),
              border: InputBorder.none,
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 14,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
