import React, { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import {
  Gauge,
  PieChart as PieChartIcon,
  TrendingUp,
  TrendingDown,
  Minus,
  ArrowUpRight,
  ArrowDownRight,
  ShieldAlert,
  Sparkles,
  AlertTriangle,
  PiggyBank,
  Loader2,
  Lightbulb,
  CheckCircle2,
  MessageCircle,
} from 'lucide-react';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import { api } from '../services/api';
import i18n from '../i18n';
import type { AnalyseFinanciere, Prediction, Budget, Categorie } from '../types';

const localeActuelle = () => (i18n.language === 'en' ? 'en-US' : 'fr-FR');
const formatMontant = (valeur: string | number) => `${Number(valeur).toLocaleString('fr-FR')} XAF`;
const formatPeriode = (debut: string, fin: string) =>
  `${new Date(debut).toLocaleDateString(localeActuelle())} → ${new Date(fin).toLocaleDateString(localeActuelle())}`;
const formatMoisCourt = (iso: string) => new Date(iso).toLocaleDateString(localeActuelle(), { month: 'short', year: '2-digit' });

// Palette volontairement multi-teintes (pas uniquement les couleurs de marque)
// pour que chaque catégorie/série d'un graphique reste immédiatement
// distinguable, même avec un grand nombre de catégories personnalisées.
const PALETTE = ['#16a34a', '#2563eb', '#f59e0b', '#db2777', '#7c3aed', '#0891b2', '#dc2626', '#ea580c', '#4f46e5', '#059669'];

const STYLE_TOOLTIP = {
  contentStyle: {
    background: 'hsl(var(--card))',
    border: '1px solid hsl(var(--border))',
    borderRadius: 12,
    fontSize: 12,
    color: 'hsl(var(--foreground))',
  },
  labelStyle: { color: 'hsl(var(--foreground))', fontWeight: 700 },
};

const AXE_STYLE = { fontSize: 11, fill: 'hsl(var(--muted-foreground))' };

type TypeAnalyse = 'HABITUDES' | 'TENDANCES' | 'COMPARAISON' | 'COMPORTEMENT';
type TypePrediction = 'DEPENSES_FUTURES' | 'RISQUE_BUDGETAIRE' | 'CAPACITE_EPARGNE';

const TYPES_ANALYSE: { valeur: TypeAnalyse; labelKey: string; icon: React.ReactNode }[] = [
  { valeur: 'HABITUDES', labelKey: 'analyse.type_habits', icon: <PieChartIcon className="h-3.5 w-3.5" /> },
  { valeur: 'TENDANCES', labelKey: 'analyse.type_trends', icon: <TrendingUp className="h-3.5 w-3.5" /> },
  { valeur: 'COMPARAISON', labelKey: 'analyse.type_comparison', icon: <ArrowUpRight className="h-3.5 w-3.5" /> },
  { valeur: 'COMPORTEMENT', labelKey: 'analyse.type_behavior', icon: <ShieldAlert className="h-3.5 w-3.5" /> },
];

const TYPES_PREDICTION: { valeur: TypePrediction; labelKey: string; icon: React.ReactNode }[] = [
  { valeur: 'DEPENSES_FUTURES', labelKey: 'analyse.pred_future_expenses', icon: <Sparkles className="h-3.5 w-3.5" /> },
  { valeur: 'RISQUE_BUDGETAIRE', labelKey: 'analyse.pred_budget_risk', icon: <AlertTriangle className="h-3.5 w-3.5" /> },
  { valeur: 'CAPACITE_EPARGNE', labelKey: 'analyse.pred_savings_capacity', icon: <PiggyBank className="h-3.5 w-3.5" /> },
];

interface Repartition {
  categorie: string;
  montant: string;
  pourcentage: number;
}

interface Tendance {
  categorie: string;
  montant_periode: string;
  moyenne_glissante_3_mois: string;
  variation_pourcentage: number | null;
}

const scoreCouleur = (score: number) =>
  score >= 70 ? 'text-forest-600 dark:text-forest-400' : score >= 40 ? 'text-amber-500' : 'text-destructive';

const ScoreFinancier: React.FC<{ score: number | null }> = ({ score }) => {
  const { t } = useTranslation();
  return (
    <div className="bg-card rounded-2xl border border-border p-5 shadow-sm flex items-center gap-4">
      <div className="p-3 rounded-xl bg-primary/10 text-primary shrink-0">
        <Gauge className="h-6 w-6" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{t('analyse.score_title')}</p>
        <p className={`text-3xl font-black tabular-nums ${score !== null ? scoreCouleur(score) : 'text-muted-foreground'}`}>
          {score !== null ? score.toFixed(1) : '—'} <span className="text-sm font-bold text-muted-foreground">/ 100</span>
        </p>
      </div>
      {score !== null && (
        <div className="w-28 shrink-0 bg-muted h-2.5 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-300 ${
              score >= 70 ? 'bg-forest-500' : score >= 40 ? 'bg-amber-500' : 'bg-destructive'
            }`}
            style={{ width: `${Math.min(Math.max(score, 0), 100)}%` }}
          />
        </div>
      )}
    </div>
  );
};

const CarteGraphique: React.FC<{ titre: string; children: React.ReactNode }> = ({ titre, children }) => (
  <div className="bg-card rounded-2xl border border-border p-5 shadow-sm">
    <h4 className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-3">{titre}</h4>
    {children}
  </div>
);

type NiveauConclusion = 'positif' | 'attention' | 'neutre';

const STYLE_CONCLUSION: Record<NiveauConclusion, { icon: React.ElementType; classes: string }> = {
  positif: { icon: CheckCircle2, classes: 'bg-forest-500/10 border-forest-500/20 text-forest-700 dark:text-forest-400' },
  attention: { icon: AlertTriangle, classes: 'bg-amber-500/10 border-amber-500/20 text-amber-800 dark:text-amber-400' },
  neutre: { icon: MessageCircle, classes: 'bg-primary/5 border-primary/20 text-foreground' },
};

// Message en langage courant, toujours affiché juste après un graphique —
// pour que la conclusion soit compréhensible même sans savoir lire un
// graphique (demande explicite : accessibilité aux non-initiés).
const Conclusion: React.FC<{ niveau: NiveauConclusion; texte: string }> = ({ niveau, texte }) => {
  const style = STYLE_CONCLUSION[niveau];
  const Icon = style.icon;
  return (
    <div className={`p-4 rounded-xl border flex items-start gap-2.5 ${style.classes}`}>
      <Icon className="h-4 w-4 shrink-0 mt-0.5" />
      <p className="text-sm font-medium leading-relaxed">{texte}</p>
    </div>
  );
};

const RenduHabitudes: React.FC<{ resultats: Record<string, unknown> }> = ({ resultats }) => {
  const { t } = useTranslation();
  const repartition = (resultats.repartition as Repartition[] | undefined) ?? [];
  const totalDepenses = resultats.total_depenses as string | undefined;

  if (repartition.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-10">{t('analyse.no_expenses_period')}</p>;
  }

  // repartition est déjà triée par pourcentage décroissant côté backend.
  const top = repartition[0];
  const concentre = top.pourcentage >= 50;
  const messageHabitudes = concentre
    ? t('analyse.habits_concentrated', { categorie: top.categorie, pourcentage: top.pourcentage, montant: formatMontant(top.montant) })
    : t('analyse.habits_balanced', { categorie: top.categorie, pourcentage: top.pourcentage, montant: formatMontant(top.montant), count: repartition.length });

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t('analyse.total_spent')} : <strong className="text-foreground">{formatMontant(totalDepenses ?? '0')}</strong>
      </p>

      <CarteGraphique titre={t('analyse.chart_breakdown')}>
        <ResponsiveContainer width="100%" height={280}>
          <PieChart>
            <Pie data={repartition} dataKey="pourcentage" nameKey="categorie" cx="50%" cy="50%" innerRadius={55} outerRadius={95} paddingAngle={3} isAnimationActive={false}>
              {repartition.map((entry, i) => (
                <Cell key={entry.categorie} fill={PALETTE[i % PALETTE.length]} stroke="hsl(var(--card))" strokeWidth={2} />
              ))}
            </Pie>
            <Tooltip formatter={(value: unknown) => `${Number(value)}%`} {...STYLE_TOOLTIP} />
            <Legend layout="vertical" verticalAlign="middle" align="right" wrapperStyle={{ fontSize: 11, lineHeight: '1.7em' }} />
          </PieChart>
        </ResponsiveContainer>
      </CarteGraphique>

      <Conclusion niveau={concentre ? 'attention' : 'positif'} texte={messageHabitudes} />

      <div className="space-y-3">
        {repartition.map((ligne, i) => (
          <div key={ligne.categorie} className="space-y-1.5">
            <div className="flex justify-between text-xs font-semibold">
              <span className="text-foreground flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full shrink-0" style={{ background: PALETTE[i % PALETTE.length] }} />
                {ligne.categorie}
              </span>
              <span className="text-muted-foreground">
                <strong className="text-foreground">{formatMontant(ligne.montant)}</strong> ({ligne.pourcentage}%)
              </span>
            </div>
            <div className="w-full bg-muted h-2 rounded-full overflow-hidden">
              <div className="h-full rounded-full transition-all duration-300" style={{ width: `${ligne.pourcentage}%`, background: PALETTE[i % PALETTE.length] }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const RenduTendances: React.FC<{ resultats: Record<string, unknown> }> = ({ resultats }) => {
  const { t } = useTranslation();
  const tendances = (resultats.tendances as Tendance[] | undefined) ?? [];

  if (tendances.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-10">{t('analyse.not_enough_trend_data')}</p>;
  }

  const labelPeriodeActuelle = t('analyse.series_current_period');
  const labelMoyenne3Mois = t('analyse.series_3month_avg');
  const donneesGraphique = tendances.map((tendance) => ({
    categorie: tendance.categorie,
    [labelPeriodeActuelle]: Number(tendance.montant_periode),
    [labelMoyenne3Mois]: Number(tendance.moyenne_glissante_3_mois),
  }));

  const enForteHausse = tendances.filter((tendance) => tendance.variation_pourcentage !== null && tendance.variation_pourcentage > 20);
  const messageTendances = enForteHausse.length > 0
    ? t('analyse.trends_rising', {
        categories: enForteHausse.map((tendance) => tendance.categorie).join(', '),
        poste: enForteHausse.length > 1 ? t('analyse.these_expense_items') : t('analyse.this_expense_item'),
      })
    : t('analyse.trends_stable');

  return (
    <div className="space-y-4">
      <CarteGraphique titre={t('analyse.chart_trends')}>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={donneesGraphique} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="categorie" tick={AXE_STYLE} interval={0} angle={-20} textAnchor="end" height={55} />
            <YAxis tick={AXE_STYLE} />
            <Tooltip formatter={(value: unknown) => formatMontant(Number(value))} {...STYLE_TOOLTIP} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey={labelPeriodeActuelle} fill={PALETTE[1]} radius={[6, 6, 0, 0]} isAnimationActive={false} />
            <Bar dataKey={labelMoyenne3Mois} fill={PALETTE[2]} radius={[6, 6, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </CarteGraphique>

      <Conclusion niveau={enForteHausse.length > 0 ? 'attention' : 'positif'} texte={messageTendances} />

      <div className="divide-y divide-border">
        {tendances.map((tendance) => (
          <div key={tendance.categorie} className="py-3.5 flex items-center justify-between gap-3">
            <div>
              <h4 className="text-sm font-bold text-foreground">{tendance.categorie}</h4>
              <p className="text-xs text-muted-foreground">
                {formatMontant(tendance.montant_periode)} — {t('analyse.avg_3month', { montant: formatMontant(tendance.moyenne_glissante_3_mois) })}
              </p>
            </div>
            {tendance.variation_pourcentage === null ? (
              <span className="text-[11px] font-bold text-muted-foreground px-2 py-1 rounded-full bg-muted">{t('analyse.new_badge')}</span>
            ) : (
              <span
                className={`text-xs font-bold flex items-center gap-1 px-2 py-1 rounded-full ${
                  tendance.variation_pourcentage > 0
                    ? 'text-destructive bg-destructive/10'
                    : tendance.variation_pourcentage < 0
                    ? 'text-forest-600 dark:text-forest-400 bg-forest-500/10'
                    : 'text-muted-foreground bg-muted'
                }`}
              >
                {tendance.variation_pourcentage > 0 ? (
                  <TrendingUp className="h-3.5 w-3.5" />
                ) : tendance.variation_pourcentage < 0 ? (
                  <TrendingDown className="h-3.5 w-3.5" />
                ) : (
                  <Minus className="h-3.5 w-3.5" />
                )}
                <span>{tendance.variation_pourcentage > 0 ? '+' : ''}{tendance.variation_pourcentage}%</span>
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

const CarteComparaison: React.FC<{ titre: string; actuelle: number; precedente: number; inverse?: boolean }> = ({
  titre, actuelle, precedente, inverse,
}) => {
  const { t } = useTranslation();
  const hausse = actuelle > precedente;
  const stable = actuelle === precedente;
  const bon = inverse ? hausse : !hausse;
  return (
    <div className="bg-card rounded-2xl border border-border p-5 shadow-sm space-y-2">
      <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{titre}</p>
      <p className="text-xl font-black text-foreground tabular-nums">{formatMontant(actuelle)}</p>
      <p className="text-xs text-muted-foreground">{t('analyse.previous_period', { montant: formatMontant(precedente) })}</p>
      {!stable && (
        <span className={`inline-flex items-center gap-1 text-xs font-bold ${bon ? 'text-forest-600 dark:text-forest-400' : 'text-destructive'}`}>
          {hausse ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
          <span>{precedente > 0 ? `${Math.abs(Math.round(((actuelle - precedente) / precedente) * 100))}%` : '—'}</span>
        </span>
      )}
    </div>
  );
};

const RenduComparaison: React.FC<{ resultats: Record<string, unknown> }> = ({ resultats }) => {
  const { t } = useTranslation();
  const depActuelle = Number(resultats.depenses_periode_actuelle ?? 0);
  const depPrecedente = Number(resultats.depenses_periode_precedente ?? 0);
  const revActuelle = Number(resultats.revenus_periode_actuelle ?? 0);
  const revPrecedente = Number(resultats.revenus_periode_precedente ?? 0);

  const labelActuelle = t('analyse.series_current');
  const labelPrecedente = t('analyse.series_previous');
  const donneesGraphique = [
    { categorie: t('transactions.expenses'), [labelActuelle]: depActuelle, [labelPrecedente]: depPrecedente },
    { categorie: t('transactions.income'), [labelActuelle]: revActuelle, [labelPrecedente]: revPrecedente },
  ];

  const variationDepenses = depPrecedente > 0 ? Math.round(((depActuelle - depPrecedente) / depPrecedente) * 100) : null;
  const variationRevenus = revPrecedente > 0 ? Math.round(((revActuelle - revPrecedente) / revPrecedente) * 100) : null;
  const depensesEnBaisse = variationDepenses !== null && variationDepenses <= 0;
  const depensesEnForteHausse = variationDepenses !== null && variationDepenses > 15;
  const revenusEnHausse = variationRevenus !== null && variationRevenus > 0;
  const revenusEnBaisse = variationRevenus !== null && variationRevenus < 0;

  const phraseDepenses = variationDepenses === null
    ? t('analyse.not_enough_compare_data')
    : depensesEnForteHausse
    ? t('analyse.expenses_sharp_rise', { percent: Math.abs(variationDepenses) })
    : variationDepenses === 0
    ? t('analyse.expenses_stable')
    : t('analyse.expenses_decreased', { percent: Math.abs(variationDepenses) });

  const phraseRevenus = variationRevenus === null
    ? ''
    : revenusEnHausse
    ? t('analyse.income_increased', { percent: variationRevenus })
    : revenusEnBaisse
    ? t('analyse.income_decreased', { percent: Math.abs(variationRevenus) })
    : '';

  // Le niveau global tient compte des DEUX signaux — jamais "positif" si l'un
  // des deux se dégrade, pour ne pas afficher un message rassurant à côté
  // d'une info inquiétante (ex. dépenses en baisse mais revenus en chute).
  let niveauComparaison: NiveauConclusion;
  let messageComparaison: string;
  if (depensesEnForteHausse || revenusEnBaisse) {
    niveauComparaison = 'attention';
    const conseil = depensesEnForteHausse ? t('analyse.identify_cause_hint') : '';
    messageComparaison = `${phraseDepenses}${phraseRevenus}${conseil}`;
  } else if (depensesEnBaisse || revenusEnHausse) {
    niveauComparaison = 'positif';
    messageComparaison = `${phraseDepenses}${phraseRevenus}${t('analyse.good_management')}`;
  } else {
    niveauComparaison = 'neutre';
    messageComparaison = t('analyse.not_enough_compare_data_full');
  }

  return (
    <div className="space-y-4">
      <CarteGraphique titre={t('analyse.chart_comparison')}>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={donneesGraphique} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="categorie" tick={AXE_STYLE} />
            <YAxis tick={AXE_STYLE} />
            <Tooltip formatter={(value: unknown) => formatMontant(Number(value))} {...STYLE_TOOLTIP} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            <Bar dataKey={labelActuelle} fill={PALETTE[1]} radius={[6, 6, 0, 0]} isAnimationActive={false} />
            <Bar dataKey={labelPrecedente} fill={PALETTE[5]} radius={[6, 6, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </CarteGraphique>

      <Conclusion niveau={niveauComparaison} texte={messageComparaison} />

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <CarteComparaison titre={t('transactions.expenses')} actuelle={depActuelle} precedente={depPrecedente} />
        <CarteComparaison titre={t('transactions.income')} actuelle={revActuelle} precedente={revPrecedente} inverse />
      </div>
    </div>
  );
};

const StatComportement: React.FC<{ label: string; valeur: number; alerte?: boolean }> = ({ label, valeur, alerte }) => (
  <div className="bg-card rounded-2xl border border-border p-5 shadow-sm text-center space-y-1.5">
    <p className={`text-2xl font-black tabular-nums ${alerte && valeur > 0 ? 'text-destructive' : 'text-foreground'}`}>{valeur}</p>
    <p className="text-xs font-semibold text-muted-foreground">{label}</p>
  </div>
);

const RenduComportement: React.FC<{ resultats: Record<string, unknown> }> = ({ resultats }) => {
  const { t } = useTranslation();
  const suspectes = Number(resultats.transactions_suspectes ?? 0);
  const depasses = Number(resultats.budgets_depasses ?? 0);
  const actifs = Number(resultats.nombre_budgets_actifs ?? 0);

  const labelSuspectes = t('analyse.suspicious_transactions');
  const labelDepasses = t('analyse.exceeded_budgets');
  const labelActifs = t('analyse.active_budgets');
  const donneesGraphique = [
    { label: labelSuspectes, valeur: suspectes },
    { label: labelDepasses, valeur: depasses },
    { label: labelActifs, valeur: actifs },
  ];

  const rienASignaler = suspectes === 0 && depasses === 0;
  let messageComportement: string;
  if (rienASignaler) {
    messageComportement = t('analyse.nothing_to_report');
  } else {
    const points: string[] = [];
    if (suspectes > 0) points.push(t('analyse.suspicious_count', { count: suspectes }));
    if (depasses > 0) points.push(t('analyse.exceeded_count', { count: depasses }));
    messageComportement = t('analyse.points_to_watch', { points: points.join(` ${t('common.and')} `) });
  }

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatComportement label={labelSuspectes} valeur={suspectes} alerte />
        <StatComportement label={labelDepasses} valeur={depasses} alerte />
        <StatComportement label={labelActifs} valeur={actifs} />
      </div>

      <CarteGraphique titre={t('analyse.overview_title')}>
        <ResponsiveContainer width="100%" height={180}>
          <BarChart layout="vertical" data={donneesGraphique} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
            <XAxis type="number" allowDecimals={false} tick={AXE_STYLE} />
            <YAxis type="category" dataKey="label" tick={AXE_STYLE} width={130} />
            <Tooltip {...STYLE_TOOLTIP} />
            <Bar dataKey="valeur" radius={[0, 6, 6, 0]} isAnimationActive={false}>
              {donneesGraphique.map((d, i) => (
                <Cell key={d.label} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </CarteGraphique>

      <Conclusion niveau={rienASignaler ? 'positif' : 'attention'} texte={messageComportement} />
    </div>
  );
};

const RENDUS_ANALYSE: Record<TypeAnalyse, React.FC<{ resultats: Record<string, unknown> }>> = {
  HABITUDES: RenduHabitudes,
  TENDANCES: RenduTendances,
  COMPARAISON: RenduComparaison,
  COMPORTEMENT: RenduComportement,
};

const niveauConfianceCouleur = (niveau: number) => (niveau >= 0.7 ? PALETTE[0] : niveau >= 0.4 ? PALETTE[2] : PALETTE[6]);

const GraphiqueHistoriqueScore: React.FC<{ historique: AnalyseFinanciere[]; scoreActuel: number | null }> = ({ historique, scoreActuel }) => {
  const { t } = useTranslation();
  const donnees = [
    ...[...historique].reverse().map((a) => ({
      label: formatMoisCourt(a.periode_debut),
      score: a.score_financier ?? 0,
      estimation: false,
    })),
    { label: t('analyse.this_month'), score: scoreActuel ?? 0, estimation: true },
  ];

  return (
    <CarteGraphique titre={t('analyse.score_evolution')}>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={donnees} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
          <XAxis dataKey="label" tick={AXE_STYLE} />
          <YAxis domain={[0, 100]} tick={AXE_STYLE} />
          <Tooltip formatter={(value: unknown) => `${value} / 100`} {...STYLE_TOOLTIP} />
          <Bar dataKey="score" radius={[6, 6, 0, 0]} isAnimationActive={false}>
            {donnees.map((d) => (
              <Cell key={d.label} fill={d.estimation ? PALETTE[1] : PALETTE[4]} fillOpacity={d.estimation ? 1 : 0.65} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </CarteGraphique>
  );
};

const GraphiqueHistoriquePrediction: React.FC<{ historique: Prediction[]; estimationActuelle: Prediction }> = ({
  historique, estimationActuelle,
}) => {
  const { t } = useTranslation();
  const donnees = [
    ...[...historique].reverse().map((p) => ({
      label: formatMoisCourt(p.periode_debut),
      montant: Number(p.montant_predit ?? 0),
      estimation: false,
    })),
    {
      label: t('analyse.estimation'),
      montant: Number(estimationActuelle.montant_predit ?? 0),
      estimation: true,
    },
  ];

  return (
    <CarteGraphique titre={t('analyse.monthly_evolution')}>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={donnees} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
          <XAxis dataKey="label" tick={AXE_STYLE} />
          <YAxis tick={AXE_STYLE} />
          <Tooltip formatter={(value: unknown) => formatMontant(Number(value))} {...STYLE_TOOLTIP} />
          <Bar dataKey="montant" radius={[6, 6, 0, 0]} isAnimationActive={false}>
            {donnees.map((d) => (
              <Cell key={d.label} fill={d.estimation ? PALETTE[1] : PALETTE[4]} fillOpacity={d.estimation ? 1 : 0.65} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </CarteGraphique>
  );
};

const GraphiqueRisqueBudgetaire: React.FC<{ budgets: Budget[]; categories: Categorie[] }> = ({ budgets, categories }) => {
  const { t } = useTranslation();
  const nomCategorie = (id: number) => categories.find((c) => c.id_categorie === id)?.nom ?? t('modals.budget.category_fallback', { id });

  if (budgets.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-6">{t('analyse.no_active_budgets')}</p>;
  }

  const labelDepense = t('analyse.spent');
  const labelLimite = t('analyse.limit');
  const donnees = budgets.map((b) => ({
    categorie: nomCategorie(b.id_categorie),
    [labelDepense]: Number(b.montant_depense),
    [labelLimite]: Number(b.montant_limite),
    depasse: b.est_depasse,
  }));

  return (
    <CarteGraphique titre={t('analyse.budget_vs_limit_chart')}>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={donnees} margin={{ top: 8, right: 8, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
          <XAxis dataKey="categorie" tick={AXE_STYLE} interval={0} angle={-20} textAnchor="end" height={55} />
          <YAxis tick={AXE_STYLE} />
          <Tooltip formatter={(value: unknown) => formatMontant(Number(value))} {...STYLE_TOOLTIP} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey={labelDepense} radius={[6, 6, 0, 0]} isAnimationActive={false}>
            {donnees.map((d) => (
              <Cell key={d.categorie} fill={d.depasse ? PALETTE[6] : PALETTE[1]} />
            ))}
          </Bar>
          <Bar dataKey={labelLimite} fill="hsl(var(--muted-foreground))" fillOpacity={0.35} radius={[6, 6, 0, 0]} isAnimationActive={false} />
        </BarChart>
      </ResponsiveContainer>
    </CarteGraphique>
  );
};

interface RenduPredictionProps {
  prediction: Prediction;
  historique: Prediction[];
  budgetsRisque: Budget[];
  categoriesRisque: Categorie[];
}

const conclusionPrediction = (prediction: Prediction, budgetsRisque: Budget[], t: TFunction): { niveau: NiveauConclusion; texte: string } => {
  if (prediction.type === 'RISQUE_BUDGETAIRE') {
    const budgetsDejaDepasses = budgetsRisque.filter((b) => b.est_depasse).length;
    if (budgetsDejaDepasses > 0) {
      return {
        niveau: 'attention',
        texte: t('analyse.budgets_exceeded_now', { count: budgetsDejaDepasses }),
      };
    }
    if (prediction.montant_predit !== null) {
      return {
        niveau: 'attention',
        texte: t('analyse.budget_risk_soon'),
      };
    }
    return {
      niveau: 'positif',
      texte: t('analyse.budget_risk_none'),
    };
  }

  if (prediction.type === 'CAPACITE_EPARGNE') {
    const montant = Number(prediction.montant_predit ?? 0);
    if (montant > 0) {
      return {
        niveau: 'positif',
        texte: t('analyse.savings_capacity_positive'),
      };
    }
    return {
      niveau: 'attention',
      texte: t('analyse.savings_capacity_negative'),
    };
  }

  // DEPENSES_FUTURES : ni bon ni mauvais signe en soi, c'est une simple projection.
  return {
    niveau: 'neutre',
    texte: t('analyse.future_expenses_note'),
  };
};

const RenduPrediction: React.FC<RenduPredictionProps> = ({ prediction, historique, budgetsRisque, categoriesRisque }) => {
  const { t } = useTranslation();
  const conclusion = conclusionPrediction(prediction, budgetsRisque, t);

  return (
    <div className="space-y-4">
      <div className="bg-card rounded-2xl border border-border p-6 shadow-sm space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1">{t('analyse.estimated_amount')}</p>
            <p className="text-3xl font-black text-primary tabular-nums">
              {prediction.montant_predit !== null ? formatMontant(prediction.montant_predit) : '—'}
            </p>
          </div>
          {prediction.niveau_confiance !== null && (
            <div className="flex items-center gap-2.5 shrink-0">
              <div className="w-24 bg-muted h-2 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${Math.round(prediction.niveau_confiance * 100)}%`, background: niveauConfianceCouleur(prediction.niveau_confiance) }}
                />
              </div>
              <span className="text-xs font-bold text-muted-foreground whitespace-nowrap">
                {t('analyse.confidence', { percent: Math.round(prediction.niveau_confiance * 100) })}
              </span>
            </div>
          )}
        </div>

        {prediction.recommandations && (
          <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 flex items-start gap-2.5">
            <Lightbulb className="h-4 w-4 text-primary shrink-0 mt-0.5" />
            <p className="text-sm text-foreground leading-relaxed">{prediction.recommandations}</p>
          </div>
        )}
      </div>

      {prediction.type === 'RISQUE_BUDGETAIRE' ? (
        <GraphiqueRisqueBudgetaire budgets={budgetsRisque} categories={categoriesRisque} />
      ) : historique.length > 0 ? (
        <GraphiqueHistoriquePrediction historique={historique} estimationActuelle={prediction} />
      ) : null}

      <Conclusion niveau={conclusion.niveau} texte={conclusion.texte} />
    </div>
  );
};

export const AnalyseSection: React.FC = () => {
  const { t } = useTranslation();
  const [mode, setMode] = useState<'analyse' | 'prediction'>('analyse');
  const [typeAnalyse, setTypeAnalyse] = useState<TypeAnalyse>('HABITUDES');
  const [typePrediction, setTypePrediction] = useState<TypePrediction>('DEPENSES_FUTURES');
  const [analyse, setAnalyse] = useState<AnalyseFinanciere | null>(null);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [historiquePrediction, setHistoriquePrediction] = useState<Prediction[]>([]);
  const [historiqueAnalyse, setHistoriqueAnalyse] = useState<AnalyseFinanciere[]>([]);
  const [budgetsRisque, setBudgetsRisque] = useState<Budget[]>([]);
  const [categoriesRisque, setCategoriesRisque] = useState<Categorie[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const charger = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (mode === 'analyse') {
        setAnalyse(await api.request<AnalyseFinanciere>(`/analyse/${typeAnalyse}`));
      } else {
        setPrediction(await api.request<Prediction>(`/analyse/predictions/${typePrediction}`));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('analyse.error_generic'));
    } finally {
      setIsLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode, typeAnalyse, typePrediction]);

  useEffect(() => {
    // Chargement à chaque changement d'onglet/type — recalculée en direct
    // côté serveur, jamais mise en cache côté client. Pas une synchronisation
    // d'état dérivé d'un rendu précédent.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    charger();
  }, [charger]);

  useEffect(() => {
    // Historique des snapshots mensuels de l'analyse — chargé séparément de
    // l'analyse courante (source différente), jamais une synchronisation
    // d'état dérivé d'un rendu précédent.
    if (mode !== 'analyse') return;
    api
      .request<AnalyseFinanciere[]>(`/analyse/${typeAnalyse}/historique`)
      .then(setHistoriqueAnalyse)
      .catch(() => setHistoriqueAnalyse([]));
  }, [mode, typeAnalyse]);

  useEffect(() => {
    // Données complémentaires pour les graphiques des prédictions — chargées
    // séparément de la prédiction elle-même (source différente), jamais une
    // synchronisation d'état dérivé d'un rendu précédent.
    if (mode !== 'prediction') return;
    if (typePrediction === 'RISQUE_BUDGETAIRE') {
      Promise.all([api.request<Budget[]>('/budgets'), api.request<Categorie[]>('/categories')])
        .then(([b, c]) => {
          setBudgetsRisque(b);
          setCategoriesRisque(c);
        })
        .catch(() => {
          setBudgetsRisque([]);
          setCategoriesRisque([]);
        });
    } else {
      api
        .request<Prediction[]>(`/analyse/predictions/${typePrediction}/historique`)
        .then(setHistoriquePrediction)
        .catch(() => setHistoriquePrediction([]));
    }
  }, [mode, typePrediction]);

  const RenduActif = analyse ? RENDUS_ANALYSE[analyse.type] : null;

  return (
    <div className="space-y-6">
      <ScoreFinancier score={analyse?.score_financier ?? null} />

      <div className="inline-flex rounded-xl bg-muted p-1 gap-1">
        <button
          onClick={() => setMode('analyse')}
          className={`text-xs font-bold px-4 py-2 rounded-lg transition-colors ${
            mode === 'analyse' ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          {t('analyse.tab_analysis')}
        </button>
        <button
          onClick={() => setMode('prediction')}
          className={`text-xs font-bold px-4 py-2 rounded-lg transition-colors ${
            mode === 'prediction' ? 'bg-card text-primary shadow-sm' : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          {t('analyse.tab_predictions')}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        {mode === 'analyse'
          ? TYPES_ANALYSE.map((item) => (
              <button
                key={item.valeur}
                onClick={() => setTypeAnalyse(item.valeur)}
                className={`flex items-center gap-1.5 text-xs font-bold px-3.5 py-2 rounded-xl border transition-colors ${
                  typeAnalyse === item.valeur
                    ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                    : 'bg-card text-muted-foreground border-border hover:text-foreground'
                }`}
              >
                {item.icon}
                <span>{t(item.labelKey)}</span>
              </button>
            ))
          : TYPES_PREDICTION.map((item) => (
              <button
                key={item.valeur}
                onClick={() => setTypePrediction(item.valeur)}
                className={`flex items-center gap-1.5 text-xs font-bold px-3.5 py-2 rounded-xl border transition-colors ${
                  typePrediction === item.valeur
                    ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                    : 'bg-card text-muted-foreground border-border hover:text-foreground'
                }`}
              >
                {item.icon}
                <span>{t(item.labelKey)}</span>
              </button>
            ))}
      </div>

      {(mode === 'analyse' ? analyse : prediction) && (
        <p className="text-xs text-muted-foreground">
          {t('analyse.period_analyzed', { periode: formatPeriode((mode === 'analyse' ? analyse : prediction)!.periode_debut, (mode === 'analyse' ? analyse : prediction)!.periode_fin) })}
        </p>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="p-4 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-sm flex items-center justify-between">
          <span>{error}</span>
          <button onClick={charger} className="font-bold underline shrink-0 ml-3">{t('common.retry')}</button>
        </div>
      ) : mode === 'analyse' ? (
        analyse && RenduActif && (
          <div className="space-y-4">
            <RenduActif key={analyse.type} resultats={analyse.resultats ?? {}} />
            {historiqueAnalyse.length > 0 && (
              <GraphiqueHistoriqueScore historique={historiqueAnalyse} scoreActuel={analyse.score_financier} />
            )}
          </div>
        )
      ) : (
        prediction && (
          <RenduPrediction
            key={prediction.type}
            prediction={prediction}
            historique={historiquePrediction}
            budgetsRisque={budgetsRisque}
            categoriesRisque={categoriesRisque}
          />
        )
      )}
    </div>
  );
};
