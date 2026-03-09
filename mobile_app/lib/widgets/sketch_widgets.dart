import 'package:flutter/material.dart';
import '../theme/sketch_theme.dart';

/// Reusable sketch-style card with hand-drawn border effect
class SketchBox extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final Color? borderColor;
  final double borderWidth;

  const SketchBox({
    super.key,
    required this.child,
    this.padding,
    this.borderColor,
    this.borderWidth = 2,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding ?? const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: SketchColors.paper,
        border: Border.all(
          color: borderColor ?? SketchColors.ink,
          width: borderWidth,
        ),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(2),
          topRight: Radius.circular(6),
          bottomLeft: Radius.circular(5),
          bottomRight: Radius.circular(3),
        ),
        boxShadow: [
          BoxShadow(
            color: (borderColor ?? SketchColors.ink).withOpacity(0.8),
            offset: const Offset(2, 2),
            blurRadius: 0,
          ),
          BoxShadow(
            color: (borderColor ?? SketchColors.ink).withOpacity(0.4),
            offset: const Offset(3, 3),
            blurRadius: 0,
          ),
          BoxShadow(
            color: Colors.black.withOpacity(0.03),
            offset: const Offset(0, 0),
            blurRadius: 30,
            spreadRadius: -5,
          ),
        ],
      ),
      child: child,
    );
  }
}

/// Panel title with dot indicator (matches web app's .panel-title)
class PanelTitle extends StatelessWidget {
  final String title;
  final Color dotColor;
  final Widget? trailing;

  const PanelTitle({
    super.key,
    required this.title,
    required this.dotColor,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.only(bottom: 6),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: SketchColors.paperLine, width: 1.5),
        ),
      ),
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              title,
              style: SketchTheme.sketchFont.copyWith(
                fontSize: 16,
                fontWeight: FontWeight.w700,
                color: SketchColors.ink,
              ),
            ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

/// Status indicator matching .status-item styles
class StatusIndicator extends StatelessWidget {
  final String label;
  final String value;
  final String level; // 'ok', 'warn', 'alert', 'danger'
  final String emoji;

  const StatusIndicator({
    super.key,
    required this.label,
    required this.value,
    required this.level,
    required this.emoji,
  });

  Color get _bgColor {
    switch (level) {
      case 'ok':
        return SketchColors.focusedBg;
      case 'warn':
        return SketchColors.warnBg;
      case 'alert':
        return SketchColors.alertBg;
      case 'danger':
        return SketchColors.dangerBg;
      default:
        return SketchColors.paper;
    }
  }

  Color get _borderColor {
    switch (level) {
      case 'ok':
        return SketchColors.focused;
      case 'warn':
        return SketchColors.warn;
      case 'alert':
        return SketchColors.alert;
      case 'danger':
        return SketchColors.danger;
      default:
        return SketchColors.ink;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
      decoration: BoxDecoration(
        color: _bgColor,
        border: Border.all(color: _borderColor, width: 2),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(2),
          topRight: Radius.circular(6),
          bottomLeft: Radius.circular(5),
          bottomRight: Radius.circular(3),
        ),
        boxShadow: [
          BoxShadow(
            color: _borderColor.withOpacity(0.3),
            offset: const Offset(1, 1),
            blurRadius: 0,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$emoji $label',
            style: SketchTheme.monoFont.copyWith(
              fontSize: 9,
              letterSpacing: 1,
              color: SketchColors.pencil,
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: SketchTheme.sketchFont.copyWith(
              fontSize: 16,
              fontWeight: FontWeight.w700,
              color: _borderColor,
            ),
          ),
        ],
      ),
    );
  }
}

/// Sketch-style progress bar matching .sketch-progress
class SketchProgressBar extends StatelessWidget {
  final double value; // 0.0 to 1.0
  final Color color;
  final double height;

  const SketchProgressBar({
    super.key,
    required this.value,
    required this.color,
    this.height = 18,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      height: height,
      decoration: BoxDecoration(
        color: SketchColors.paperDark,
        border: Border.all(color: SketchColors.ink, width: 2),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(1),
          topRight: Radius.circular(4),
          bottomLeft: Radius.circular(3),
          bottomRight: Radius.circular(2),
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(2),
        child: AnimatedFractionallySizedBox(
          duration: const Duration(milliseconds: 500),
          curve: Curves.easeOutCubic,
          alignment: Alignment.centerLeft,
          widthFactor: value.clamp(0.0, 1.0),
          child: Container(
            decoration: BoxDecoration(
              color: color,
              // Diagonal pencil-stroke texture
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  color,
                  color.withOpacity(0.85),
                  color,
                  color.withOpacity(0.85),
                  color,
                ],
                stops: const [0.0, 0.2, 0.4, 0.6, 1.0],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// Animated fractionally sized box
class AnimatedFractionallySizedBox extends StatelessWidget {
  final Duration duration;
  final Curve curve;
  final AlignmentGeometry alignment;
  final double widthFactor;
  final Widget child;

  const AnimatedFractionallySizedBox({
    super.key,
    required this.duration,
    required this.curve,
    required this.alignment,
    required this.widthFactor,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(end: widthFactor),
      duration: duration,
      curve: curve,
      builder: (context, value, child) {
        return FractionallySizedBox(
          alignment: alignment,
          widthFactor: value,
          child: child,
        );
      },
      child: child,
    );
  }
}

/// Badge / Pill widget matching .pill
class SketchPill extends StatelessWidget {
  final String text;
  final Color? color;
  final Color? bgColor;
  final bool animate;

  const SketchPill({
    super.key,
    required this.text,
    this.color,
    this.bgColor,
    this.animate = false,
  });

  @override
  Widget build(BuildContext context) {
    final c = color ?? SketchColors.paper;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: bgColor ?? Colors.transparent,
        border: Border.all(color: c.withOpacity(0.5), width: 1),
        borderRadius: BorderRadius.circular(2),
      ),
      child: Text(
        text.toUpperCase(),
        style: SketchTheme.monoFont.copyWith(
          fontSize: 10,
          letterSpacing: 1,
          color: c,
        ),
      ),
    );
  }
}

/// Metric card matching .metric-card
class MetricCard extends StatelessWidget {
  final String label;
  final String value;
  final String sub;

  const MetricCard({
    super.key,
    required this.label,
    required this.value,
    required this.sub,
  });

  @override
  Widget build(BuildContext context) {
    return SketchBox(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label.toUpperCase(),
            style: SketchTheme.monoFont.copyWith(
              fontSize: 9,
              letterSpacing: 1,
              color: SketchColors.pencil,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: SketchTheme.sketchFont.copyWith(
              fontSize: 22,
              fontWeight: FontWeight.w700,
              color: SketchColors.ink,
            ),
          ),
          Text(
            sub,
            style: SketchTheme.monoFont.copyWith(
              fontSize: 8,
              color: SketchColors.inkVeryFaint,
            ),
          ),
        ],
      ),
    );
  }
}
