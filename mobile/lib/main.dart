import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // `.env` n'est jamais commité (voir .gitignore) — copier .env.example en
  // .env avant de lancer l'app, comme pour backend/ et frontend/.
  await dotenv.load(fileName: '.env');

  runApp(const ProviderScope(child: MyNkapApp()));
}
