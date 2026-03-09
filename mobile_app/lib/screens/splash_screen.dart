import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/modern_theme.dart';
import 'login_screen.dart';

class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _scanController;
  late Animation<double> _scanAnimation;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _scanController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();

    _scanAnimation = Tween<double>(begin: -1.0, end: 1.0).animate(
      CurvedAnimation(parent: _scanController, curve: Curves.easeInOutSine),
    );

    _navigateToLogin();
  }

  Future<void> _navigateToLogin() async {
    await Future.delayed(const Duration(seconds: 4));
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        transitionDuration: const Duration(milliseconds: 800),
        pageBuilder: (_, __, ___) => const LoginScreen(),
        transitionsBuilder: (_, anim, __, child) {
          return FadeTransition(opacity: anim, child: child);
        },
      ),
    );
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _scanController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ModernColors.bgPrimary,
      body: Stack(
        children: [
          // Cyber grid background
          CustomPaint(
            painter: _GridPainter(progress: _scanController),
            size: Size.infinite,
          ),

          // Scanning Line
          AnimatedBuilder(
            animation: _scanAnimation,
            builder: (context, child) {
              return Positioned(
                top:
                    (MediaQuery.of(context).size.height / 2) +
                    (_scanAnimation.value *
                        MediaQuery.of(context).size.height /
                        2),
                left: 0,
                right: 0,
                child: Container(
                  height: 2,
                  decoration: BoxDecoration(
                    boxShadow: [
                      BoxShadow(
                        color: ModernColors.accentCyan.withOpacity(0.5),
                        blurRadius: 10,
                        spreadRadius: 2,
                      ),
                    ],
                    gradient: LinearGradient(
                      colors: [
                        Colors.transparent,
                        ModernColors.accentCyan.withOpacity(0.8),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              );
            },
          ),

          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                // Animated Eye/Camera Icon
                AnimatedBuilder(
                  animation: _pulseController,
                  builder: (context, child) {
                    return Transform.scale(
                      scale: 1.0 + (_pulseController.value * 0.1),
                      child: Container(
                        padding: const EdgeInsets.all(32),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: ModernColors.glassBg,
                          border: Border.all(
                            color: ModernColors.accentCyan.withOpacity(0.3),
                            width: 2,
                          ),
                          boxShadow: [
                            BoxShadow(
                              color: ModernColors.accentCyan.withOpacity(
                                0.2 * _pulseController.value,
                              ),
                              blurRadius: 40,
                              spreadRadius: 10,
                            ),
                          ],
                        ),
                        child: Icon(
                          Icons.visibility_outlined,
                          size: 80,
                          color: ModernColors.accentCyan.withOpacity(
                            0.8 + 0.2 * _pulseController.value,
                          ),
                        ),
                      ),
                    );
                  },
                ),

                const SizedBox(height: 48),

                // Title
                Text(
                  'SILENT INVIGILATOR',
                  style: GoogleFonts.outfit(
                    fontSize: 32,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 4,
                    foreground: Paint()
                      ..shader = ModernTheme.linearGradientShader,
                  ),
                ),

                const SizedBox(height: 16),

                Text(
                  'AI SURVEILLANCE & MONITORING SYSTEM',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 12,
                    letterSpacing: 2,
                    color: ModernColors.textSecondary,
                  ),
                ),

                const SizedBox(height: 64),

                // Loading bar
                Container(
                  width: 200,
                  height: 2,
                  decoration: BoxDecoration(
                    color: ModernColors.bgTertiary,
                    borderRadius: BorderRadius.circular(2),
                  ),
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(2),
                    child: AnimatedBuilder(
                      animation: _scanController,
                      builder: (context, child) {
                        return FractionallySizedBox(
                          alignment: Alignment.centerLeft,
                          widthFactor: _scanController.value,
                          child: Container(
                            decoration: const BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  ModernColors.accentCyan,
                                  ModernColors.accentPurple,
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
                ),

                const SizedBox(height: 16),

                AnimatedBuilder(
                  animation: _pulseController,
                  builder: (context, child) {
                    return Opacity(
                      opacity: 0.5 + 0.5 * _pulseController.value,
                      child: Text(
                        'INITIALIZING...',
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 10,
                          letterSpacing: 2,
                          color: ModernColors.accentCyan,
                        ),
                      ),
                    );
                  },
                ),
              ],
            ),
          ),

          // Footer
          Positioned(
            bottom: 32,
            left: 0,
            right: 0,
            child: Center(
              child: Text(
                'SYSTEM v2.0.0 • GROUP 10',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 10,
                  color: ModernColors.textMuted,
                  letterSpacing: 1,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GridPainter extends CustomPainter {
  final Animation<double> progress;
  _GridPainter({required this.progress}) : super(repaint: progress);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = ModernColors.glassBorder.withOpacity(0.05)
      ..strokeWidth = 1.0;

    const double spacing = 40.0;

    // Draw vertical lines
    for (double i = 0; i < size.width; i += spacing) {
      canvas.drawLine(Offset(i, 0), Offset(i, size.height), paint);
    }

    // Draw horizontal lines
    final offset = (progress.value * spacing) % spacing;
    for (double i = offset; i < size.height; i += spacing) {
      canvas.drawLine(Offset(0, i), Offset(size.width, i), paint);
    }
  }

  @override
  bool shouldRepaint(_GridPainter oldDelegate) => true;
}
