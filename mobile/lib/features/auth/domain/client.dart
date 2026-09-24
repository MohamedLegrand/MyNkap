import 'profile.dart';

/// Miroir de `ClientOut` (backend/app/modules/auth/schemas.py) — le client
/// connecté, tel que renvoyé par `GET /auth/me`.
class Client {
  const Client({
    required this.idClient,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.phone,
    required this.estActif,
    required this.statutCompte,
    required this.dateCreation,
    this.profile,
  });

  final int idClient;
  final String email;
  final String firstName;
  final String lastName;
  final String phone;
  final bool estActif;
  final String statutCompte;
  final DateTime dateCreation;
  final Profile? profile;

  String get nomComplet => '$firstName $lastName'.trim();

  factory Client.fromJson(Map<String, dynamic> json) {
    return Client(
      idClient: json['id_client'] as int,
      email: json['email'] as String,
      firstName: json['first_name'] as String,
      lastName: json['last_name'] as String,
      phone: json['phone'] as String,
      estActif: json['est_actif'] as bool,
      statutCompte: json['statut_compte'] as String? ?? 'ACTIF',
      dateCreation: DateTime.parse(json['date_creation'] as String),
      profile: json['profile'] == null
          ? null
          : Profile.fromJson(json['profile'] as Map<String, dynamic>),
    );
  }
}
