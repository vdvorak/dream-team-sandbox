import 'package:go_router/go_router.dart';

import 'example/example_page.dart';

/// Central routing. A new screen = a new GoRoute (not ad-hoc Navigator.push).
final router = GoRouter(
  routes: [GoRoute(path: '/', builder: (_, __) => const ExamplePage())],
);
