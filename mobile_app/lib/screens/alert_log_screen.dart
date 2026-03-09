import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../theme/sketch_theme.dart';
import '../services/invigilator_service.dart';

class AlertLogScreen extends StatelessWidget {
  final InvigilatorService service;

  const AlertLogScreen({super.key, required this.service});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Container(
          decoration: BoxDecoration(
            color: SketchColors.paper,
            border: const Border(
              left: BorderSide(
                color: SketchColors.ink,
                width: 5,
                style: BorderStyle.solid,
              ),
            ),
          ),
          child: Column(
            children: [
              // Nav bar
              Padding(
                padding: const EdgeInsets.all(16),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    GestureDetector(
                      onTap: () => Navigator.pop(context),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          border: Border.all(color: SketchColors.ink),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          '← Back to Monitoring',
                          style: GoogleFonts.specialElite(
                            fontSize: 12,
                            color: SketchColors.ink,
                          ),
                        ),
                      ),
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Text(
                          'Invigilator: admin',
                          style: GoogleFonts.specialElite(
                            fontSize: 11,
                            fontWeight: FontWeight.bold,
                            color: SketchColors.ink,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),

              // Title
              Text(
                'Suspicious Activity Log',
                style: GoogleFonts.caveat(
                  fontSize: 32,
                  fontWeight: FontWeight.w700,
                  color: SketchColors.ink,
                ),
              ),
              Text(
                '— Confidential Examination Record —',
                style: GoogleFonts.specialElite(
                  fontSize: 10,
                  color: SketchColors.pencil,
                  letterSpacing: 1,
                ),
              ),
              const SizedBox(height: 20),

              // Alert list
              Expanded(
                child: service.alertLog.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.check_circle_outline,
                              size: 48,
                              color: SketchColors.focused,
                            ),
                            const SizedBox(height: 12),
                            Text(
                              'No suspicious incidents recorded yet.',
                              style: GoogleFonts.kalam(
                                fontSize: 14,
                                color: SketchColors.pencil,
                              ),
                            ),
                            Text(
                              'Good job!',
                              style: GoogleFonts.caveat(
                                fontSize: 20,
                                fontWeight: FontWeight.w700,
                                color: SketchColors.focused,
                              ),
                            ),
                          ],
                        ),
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemCount: service.alertLog.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 4),
                        itemBuilder: (context, index) {
                          final alert = service.alertLog[index];
                          Color alertColor;
                          Color alertBg;
                          String badge;

                          switch (alert.type) {
                            case 'danger':
                              alertColor = SketchColors.danger;
                              alertBg = SketchColors.dangerBg;
                              badge = 'CRITICAL';
                              break;
                            case 'warn':
                              alertColor = SketchColors.warn;
                              alertBg = SketchColors.warnBg;
                              badge = 'WARN';
                              break;
                            default:
                              alertColor = SketchColors.focused;
                              alertBg = SketchColors.focusedBg;
                              badge = 'INFO';
                          }

                          return Container(
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              color: index.isEven
                                  ? SketchColors.paper
                                  : SketchColors.paper.withOpacity(0.5),
                              border: Border(
                                bottom: BorderSide(
                                  color: SketchColors.paperLine,
                                  width: 1,
                                ),
                              ),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Time
                                SizedBox(
                                  width: 60,
                                  child: Text(
                                    '${alert.timestamp.hour.toString().padLeft(2, '0')}:${alert.timestamp.minute.toString().padLeft(2, '0')}:${alert.timestamp.second.toString().padLeft(2, '0')}',
                                    style: GoogleFonts.specialElite(
                                      fontSize: 10,
                                      color: SketchColors.pencil,
                                    ),
                                  ),
                                ),

                                // Badge
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                    vertical: 1,
                                  ),
                                  margin: const EdgeInsets.only(right: 8),
                                  decoration: BoxDecoration(
                                    color: alertBg,
                                    border: Border.all(color: alertColor),
                                    borderRadius: BorderRadius.circular(3),
                                  ),
                                  child: Text(
                                    badge,
                                    style: GoogleFonts.specialElite(
                                      fontSize: 8,
                                      color: alertColor,
                                      fontWeight: FontWeight.bold,
                                    ),
                                  ),
                                ),

                                // Message
                                Expanded(
                                  child: Text(
                                    alert.message,
                                    style: GoogleFonts.kalam(
                                      fontSize: 13,
                                      color: SketchColors.ink,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          );
                        },
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
