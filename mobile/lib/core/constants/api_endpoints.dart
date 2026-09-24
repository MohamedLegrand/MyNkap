/// Chemins de l'API MyNkap, relatifs à [Env.apiBaseUrl] (qui porte déjà le
/// préfixe `/api/v1`) — recopiés depuis les routeurs FastAPI (voir
/// `backend/app/modules/*/router.py`), une constante par ressource plutôt
/// que des chaînes éparpillées dans chaque repository.
class ApiEndpoints {
  ApiEndpoints._();

  // --- Authentification (backend/app/modules/auth/router.py) ---
  static const register = '/auth/register';
  static const login = '/auth/login';
  static const loginGoogle = '/auth/google';
  static const verifyOtp = '/auth/verify-otp';
  static const refresh = '/auth/refresh';
  static const logout = '/auth/logout';
  static const me = '/auth/me';
  static const profile = '/auth/profile';
  static const profilePhoto = '/auth/profile/photo';
  static const changePassword = '/auth/change-password';
  static const forgotPassword = '/auth/forgot-password';
  static const resetPassword = '/auth/reset-password';

  // --- Comptes financiers ---
  static const comptes = '/comptes';
  static String compte(int id) => '/comptes/$id';
  static const comptePrincipal = '/comptes/principal';

  // --- Transactions ---
  static const transactions = '/transactions';
  static String transaction(int id) => '/transactions/$id';

  // --- Budgets & catégories ---
  static const categories = '/categories';
  static const budgets = '/budgets';

  // --- Dettes & créances ---
  static const dettes = '/dettes';

  // --- Épargne ---
  static const objectifsEpargne = '/epargne';

  // --- Abonnement & paiements ---
  static const plans = '/plans';
  static const paysDisponibles = '/abonnement/pays-disponibles';
  static const abonnementPaiements = '/abonnement/paiements';
  static const abonnementDonneesVerrouillees = '/abonnement/donnees-verrouillees';

  // --- Recharges de compte ---
  static const recharges = '/recharges';

  // --- Rapports ---
  static const rapports = '/rapports';

  // --- Notifications ---
  static const notifications = '/notifications';

  // --- JARVIS (assistant IA) ---
  static const jarvisConversations = '/jarvis/conversations';

  // --- Analyse (type_analyse: COMPORTEMENT, DEPENSES...) ---
  static String analyse(String typeAnalyse) => '/analyse/$typeAnalyse';
}
