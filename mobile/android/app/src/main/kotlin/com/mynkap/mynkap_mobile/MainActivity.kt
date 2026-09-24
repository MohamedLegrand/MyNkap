package com.mynkap.mynkap_mobile

import io.flutter.embedding.android.FlutterFragmentActivity

// FlutterFragmentActivity (pas FlutterActivity) : requis par local_auth,
// qui affiche l'invite biométrique via un androidx.fragment.app.DialogFragment
// (voir la connexion biométrique du module auth).
class MainActivity : FlutterFragmentActivity()
