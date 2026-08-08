import {
  Utensils, Car, Home, HeartPulse, GraduationCap, Receipt, Gamepad2,
  ShoppingBag, MoreHorizontal, Wallet, Briefcase, ArrowLeftRight, PlusCircle,
  Plane, Gift, Smartphone, Wifi, Fuel, Baby, Dog, Dumbbell, Coffee, Shirt,
  Tv, BookOpen, PiggyBank, CreditCard, Building2, Wrench, ShieldCheck,
  Stethoscope, Pill, Landmark, HandCoins, Sparkles, Tag,
  type LucideIcon,
} from 'lucide-react';

// Catalogue fermé, miroir exact de budgets.schemas.ICONES_CATEGORIE côté
// backend. Une valeur absente de cette liste (donnée périmée, ancienne
// valeur en base) retombe simplement sur l'icône par défaut ci-dessous —
// jamais de résolution dynamique d'un nom de composant depuis une chaîne
// arbitraire, qui serait une porte ouverte à l'injection.
export const ICONES_CATEGORIE: Record<string, LucideIcon> = {
  utensils: Utensils,
  car: Car,
  home: Home,
  'heart-pulse': HeartPulse,
  'graduation-cap': GraduationCap,
  receipt: Receipt,
  'gamepad-2': Gamepad2,
  'shopping-bag': ShoppingBag,
  'more-horizontal': MoreHorizontal,
  wallet: Wallet,
  briefcase: Briefcase,
  'arrow-left-right': ArrowLeftRight,
  'plus-circle': PlusCircle,
  plane: Plane,
  gift: Gift,
  smartphone: Smartphone,
  wifi: Wifi,
  fuel: Fuel,
  baby: Baby,
  dog: Dog,
  dumbbell: Dumbbell,
  coffee: Coffee,
  shirt: Shirt,
  tv: Tv,
  'book-open': BookOpen,
  'piggy-bank': PiggyBank,
  'credit-card': CreditCard,
  'building-2': Building2,
  wrench: Wrench,
  'shield-check': ShieldCheck,
  stethoscope: Stethoscope,
  pill: Pill,
  landmark: Landmark,
  'hand-coins': HandCoins,
  sparkles: Sparkles,
};

export const ICONE_CATEGORIE_PAR_DEFAUT = Tag;
