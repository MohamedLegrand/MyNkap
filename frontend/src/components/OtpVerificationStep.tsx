import React, { useState, useEffect, useRef } from 'react';
import { ShieldCheck, Mail, ArrowLeft, RefreshCw, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

interface OtpVerificationStepProps {
  email: string;
  // Renvoie un message d'erreur si le code est invalide, ou null en cas de succès
  // (dans ce cas le parent gère la navigation, ce composant n'a rien à faire de plus).
  onVerifyCode: (otpCode: string) => Promise<string | null>;
  // Renvoie un message d'erreur si le renvoi échoue, ou null en cas de succès.
  onResend: () => Promise<string | null>;
  onBackToLogin: () => void;
}

export const OtpVerificationStep: React.FC<OtpVerificationStepProps> = ({
  email,
  onVerifyCode,
  onResend,
  onBackToLogin,
}) => {
  const [digits, setDigits] = useState<string[]>(['', '', '', '', '', '']);
  const [timer, setTimer] = useState<number>(60);
  // Dérivé de timer plutôt qu'un état séparé synchronisé par effet : évite
  // un aller-retour de rendu inutile (et le state à maintenir en double).
  const canResend = timer <= 0;
  const [isResending, setIsResending] = useState<boolean>(false);
  const [resendSuccessMsg, setResendSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);

  // Décompte du timer 60s
  useEffect(() => {
    if (timer <= 0) return;
    const interval = setInterval(() => {
      setTimer((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(interval);
  }, [timer]);

  // Focus sur la première case au montage
  useEffect(() => {
    if (inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, []);

  const handleChange = (index: number, value: string) => {
    // Ne conserver que les chiffres
    const sanitized = value.replace(/[^0-9]/g, '');
    if (!sanitized && value !== '') return;

    const newDigits = [...digits];
    newDigits[index] = sanitized.slice(-1); // prendre le dernier caractère saisi
    setDigits(newDigits);
    setErrorMsg(null);

    // Auto-advance vers la case suivante
    if (sanitized && index < 5 && inputRefs.current[index + 1]) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace') {
      if (!digits[index] && index > 0 && inputRefs.current[index - 1]) {
        // Si la case actuelle est vide, reculer d'une case
        inputRefs.current[index - 1]?.focus();
      }
    } else if (e.key === 'ArrowLeft' && index > 0) {
      inputRefs.current[index - 1]?.focus();
    } else if (e.key === 'ArrowRight' && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    e.preventDefault();
    const pastedData = e.clipboardData.getData('text').replace(/[^0-9]/g, '').slice(0, 6);
    if (pastedData) {
      const newDigits = [...digits];
      for (let i = 0; i < 6; i++) {
        newDigits[i] = pastedData[i] || '';
      }
      setDigits(newDigits);
      // Focus sur la dernière case remplie ou la dernière
      const nextFocusIndex = Math.min(pastedData.length, 5);
      inputRefs.current[nextFocusIndex]?.focus();
    }
  };

  const handleResendCode = async () => {
    if (!canResend || isResending) return;
    setIsResending(true);
    setResendSuccessMsg(null);
    setErrorMsg(null);

    const erreur = await onResend();
    setIsResending(false);

    if (erreur) {
      setErrorMsg(erreur);
      return;
    }

    setTimer(60);
    setResendSuccessMsg('Un nouveau code à 6 chiffres a été envoyé par e-mail.');
    setDigits(['', '', '', '', '', '']);
    inputRefs.current[0]?.focus();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const fullCode = digits.join('');
    if (fullCode.length < 6) {
      setErrorMsg('Veuillez saisir le code complet à 6 chiffres.');
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);

    const erreur = await onVerifyCode(fullCode);
    setIsSubmitting(false);
    if (erreur) {
      setErrorMsg(erreur);
    }
  };

  const isComplete = digits.join('').length === 6;

  return (
    <div className="space-y-6 animate-in fade-in zoom-in-95 duration-200">
      {/* Header avec Icône de Sécurité */}
      <div className="text-center space-y-3">
        <div className="mx-auto w-14 h-14 rounded-2xl bg-gradient-to-tr from-primary/20 via-primary/10 to-secondary/20 text-primary flex items-center justify-center border border-primary/20 shadow-sm">
          <ShieldCheck className="h-7 w-7 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-bold tracking-tight text-foreground">Double Authentification (OTP)</h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto leading-relaxed">
            Un code de sécurité à 6 chiffres a été envoyé par e-mail à :
          </p>
          <span className="inline-block mt-1 text-xs font-black text-primary bg-primary/10 px-3 py-1 rounded-full border border-primary/20">
            {email}
          </span>
        </div>
      </div>

      {/* Formulaire Saisie 6 Chiffres */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="flex justify-center items-center gap-2 sm:gap-3">
          {digits.map((digit, idx) => (
            <input
              key={idx}
              ref={(el) => { inputRefs.current[idx] = el; }}
              type="text"
              inputMode="numeric"
              maxLength={1}
              value={digit}
              onChange={(e) => handleChange(idx, e.target.value)}
              onKeyDown={(e) => handleKeyDown(idx, e)}
              onPaste={idx === 0 ? handlePaste : undefined}
              className={`w-11 h-13 sm:w-12 sm:h-14 text-center text-xl font-black rounded-xl border bg-background text-foreground shadow-sm transition-all focus:outline-none focus:ring-2 ${
                digit
                  ? 'border-primary ring-1 ring-primary/50 bg-primary/5'
                  : 'border-border focus:ring-secondary'
              }`}
            />
          ))}
        </div>

        {/* Message d'Erreur */}
        {errorMsg && (
          <div className="p-3 rounded-xl bg-destructive/10 text-destructive text-xs font-semibold flex items-center justify-center gap-2 border border-destructive/20">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Message de Succès Renvoi */}
        {resendSuccessMsg && (
          <div className="p-3 rounded-xl bg-forest-500/10 text-forest-600 dark:text-forest-400 text-xs font-semibold flex items-center justify-center gap-2 border border-forest-500/20">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            <span>{resendSuccessMsg}</span>
          </div>
        )}

        {/* Bouton de Validation */}
        <button
          type="submit"
          disabled={!isComplete || isSubmitting}
          className="w-full bg-primary hover:bg-primary/95 disabled:opacity-50 disabled:cursor-not-allowed text-primary-foreground font-bold py-3.5 rounded-xl transition-all shadow-md flex items-center justify-center gap-2"
        >
          {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
          <span>{isSubmitting ? 'Vérification du code...' : 'Valider et Accéder au Dashboard'}</span>
        </button>
      </form>

      {/* Renvoyer le code & Timer */}
      <div className="pt-2 border-t border-border flex flex-col items-center gap-3">
        <div className="text-xs text-muted-foreground flex items-center gap-2">
          <Mail className="h-3.5 w-3.5" />
          <span>Vous n'avez pas reçu le code ?</span>
        </div>

        {canResend ? (
          <button
            type="button"
            onClick={handleResendCode}
            disabled={isResending}
            className="text-xs font-bold text-secondary hover:underline flex items-center gap-1.5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${isResending ? 'animate-spin' : ''}`} />
            <span>{isResending ? 'Envoi du code...' : 'Renvoyer un nouveau code'}</span>
          </button>
        ) : (
          <span className="text-xs font-semibold text-muted-foreground bg-muted px-3 py-1 rounded-full border border-border">
            Renvoyer dans <strong className="text-foreground tabular-nums">00:{timer < 10 ? `0${timer}` : timer}</strong>
          </span>
        )}

        <button
          type="button"
          onClick={onBackToLogin}
          className="text-xs font-medium text-muted-foreground hover:text-foreground flex items-center gap-1 pt-1"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Retour à l'adresse e-mail</span>
        </button>
      </div>
    </div>
  );
};
