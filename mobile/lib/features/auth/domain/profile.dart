/// Miroir de `ProfileOut` (backend/app/modules/auth/schemas.py).
class Profile {
  const Profile({
    required this.idProfile,
    required this.devise,
    required this.langue,
    this.avatar,
  });

  final int idProfile;
  final String? avatar;
  final String devise;
  final String langue;

  factory Profile.fromJson(Map<String, dynamic> json) {
    return Profile(
      idProfile: json['id_profile'] as int,
      avatar: json['avatar'] as String?,
      devise: json['devise'] as String,
      langue: json['langue'] as String,
    );
  }
}
