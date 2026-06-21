import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'src/app.dart';

/// Entry point. ProviderScope (Riverpod) wraps the whole app — the state DI container.
void main() {
  runApp(const ProviderScope(child: App()));
}
