import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'screens/splash_screen.dart';
import 'theme/modern_theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: ModernColors.bgPrimary,
      statusBarIconBrightness: Brightness.light,
      systemNavigationBarColor: ModernColors.bgPrimary,
      systemNavigationBarIconBrightness: Brightness.light,
    ),
  );
  runApp(const SilentInvigilatorApp());
}

class SilentInvigilatorApp extends StatelessWidget {
  const SilentInvigilatorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Silent Invigilator',
      debugShowCheckedModeBanner: false,
      theme: ModernTheme.themeData,
      home: const SplashScreen(),
    );
  }
}
