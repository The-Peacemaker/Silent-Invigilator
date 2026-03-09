import 'package:flutter_test/flutter_test.dart';
import 'package:silent_invigilator_app/main.dart';

void main() {
  testWidgets('App launches correctly', (WidgetTester tester) async {
    await tester.pumpWidget(const SilentInvigilatorApp());
    // Just checking it builds without errors
    expect(find.byType(SilentInvigilatorApp), findsOneWidget);
  });
}
