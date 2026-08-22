import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Bot, Send, Loader2, Mic, Square, History, Plus, Trash2, AlertTriangle, Volume2, CheckCircle2, Ban, Sparkles } from 'lucide-react';
import { api } from '../services/api';
import { formatDateRelative } from '../utils/formatters';
import type { ActionIA, JarvisConversation, JarvisConversationDetail, JarvisMessage, JarvisMessageVocal } from '../types';

export const JarvisWidget: React.FC = () => {
  const { t } = useTranslation();
  const [conversations, setConversations] = useState<JarvisConversation[]>([]);
  const [conversationActuelle, setConversationActuelle] = useState<string | null>(null);
  const [messages, setMessages] = useState<JarvisMessage[]>([]);
  const [afficherHistorique, setAfficherHistorique] = useState(false);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);

  const [query, setQuery] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const historiqueRef = useRef<HTMLDivElement | null>(null);

  const [actionsEnCours, setActionsEnCours] = useState<Set<string>>(new Set());

  const messageAccueil: JarvisMessage = {
    id_message: 'accueil',
    type: 'REPONSE',
    canal: 'TEXTE',
    contenu: t('jarvis.welcome_message'),
    necessite_clarification: false,
    options_suggerees: null,
    peut_se_permettre: null,
    montant_suggere: null,
    conseil_supplementaire: null,
    actions: [],
    date_creation: new Date().toISOString(),
  };

  const chargerConversations = () => {
    api.request<JarvisConversation[]>('/jarvis/conversations')
      .then(setConversations)
      .catch(() => {});
  };

  useEffect(() => {
    chargerConversations();
  }, []);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (historiqueRef.current && !historiqueRef.current.contains(e.target as Node)) {
        setAfficherHistorique(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const ouvrirConversation = async (id: string) => {
    setAfficherHistorique(false);
    setError(null);
    setIsLoadingConversation(true);
    try {
      const detail = await api.request<JarvisConversationDetail>(`/jarvis/conversations/${id}`);
      setConversationActuelle(detail.id_conversation);
      setMessages(detail.messages);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('jarvis.conversation_not_found'));
    } finally {
      setIsLoadingConversation(false);
    }
  };

  const demarrerNouvelleConversation = () => {
    setAfficherHistorique(false);
    setConversationActuelle(null);
    setMessages([]);
    setError(null);
  };

  const supprimerConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await api.request(`/jarvis/conversations/${id}`, { method: 'DELETE' });
      setConversations((prev) => prev.filter((c) => c.id_conversation !== id));
      if (id === conversationActuelle) {
        demarrerNouvelleConversation();
      }
    } catch {
      // Échec de suppression ponctuel : la conversation reste visible,
      // l'utilisateur peut réessayer.
    }
  };

  const obtenirOuCreerConversation = async (): Promise<string> => {
    if (conversationActuelle) return conversationActuelle;
    const conversation = await api.request<JarvisConversation>('/jarvis/conversations', {
      method: 'POST',
      body: JSON.stringify({}),
    });
    setConversationActuelle(conversation.id_conversation);
    return conversation.id_conversation;
  };

  const jouerAudio = (audioBase64: string) => {
    const lecteur = new Audio(`data:audio/wav;base64,${audioBase64}`);
    lecteur.play().catch(() => {});
  };

  // JARVIS ne modifie jamais de donnée financière de sa propre initiative —
  // une action proposée reste EN_ATTENTE tant que le client n'a pas cliqué
  // ici sur Confirmer. Met à jour l'action dans le message concerné, où
  // qu'il soit dans l'historique affiché.
  const traiterAction = async (idAction: string, chemin: 'confirmer' | 'annuler') => {
    if (actionsEnCours.has(idAction)) return;
    setActionsEnCours((prev) => new Set(prev).add(idAction));
    try {
      const actionMiseAJour = await api.request<ActionIA>(`/jarvis/actions/${idAction}/${chemin}`, {
        method: 'POST',
      });
      setMessages((prev) =>
        prev.map((msg) => ({
          ...msg,
          actions: msg.actions.map((a) => (a.id_action === idAction ? actionMiseAJour : a)),
        }))
      );
      if (chemin === 'confirmer') chargerConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('jarvis.action_error'));
    } finally {
      setActionsEnCours((prev) => {
        const suivant = new Set(prev);
        suivant.delete(idAction);
        return suivant;
      });
    }
  };

  const envoyerMessageTexte = async (e: React.FormEvent) => {
    e.preventDefault();
    const question = query.trim();
    if (!question || isSending) return;

    setError(null);
    setQuery('');
    setIsSending(true);
    try {
      const idConversation = await obtenirOuCreerConversation();
      const messageOptimiste: JarvisMessage = {
        id_message: `optimiste-${Date.now()}`,
        type: 'QUESTION',
        canal: 'TEXTE',
        contenu: question,
        necessite_clarification: false,
        options_suggerees: null,
        peut_se_permettre: null,
        montant_suggere: null,
        conseil_supplementaire: null,
        actions: [],
        date_creation: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, messageOptimiste]);

      const reponse = await api.request<JarvisMessage>(`/jarvis/conversations/${idConversation}/messages`, {
        method: 'POST',
        body: JSON.stringify({ contenu: question }),
      });
      setMessages((prev) => [...prev, reponse]);
      chargerConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('jarvis.unavailable'));
    } finally {
      setIsSending(false);
    }
  };

  const envoyerMessageVocal = async (blob: Blob) => {
    setError(null);
    setIsTranscribing(true);
    try {
      const idConversation = await obtenirOuCreerConversation();
      const formData = new FormData();
      formData.append('audio', blob, `question.${blob.type.includes('webm') ? 'webm' : 'ogg'}`);

      const reponse = await api.request<JarvisMessageVocal>(
        `/jarvis/conversations/${idConversation}/messages/vocal`,
        { method: 'POST', body: formData }
      );

      if (reponse.audio_base64) {
        jouerAudio(reponse.audio_base64);
      }
      // La question transcrite n'est pas renvoyée directement (seule la
      // réponse l'est) : on recharge la conversation pour l'afficher.
      const detail = await api.request<JarvisConversationDetail>(`/jarvis/conversations/${idConversation}`);
      setMessages(detail.messages);
      chargerConversations();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('jarvis.unavailable'));
    } finally {
      setIsTranscribing(false);
    }
  };

  const basculerEnregistrement = async () => {
    if (isRecording) {
      mediaRecorderRef.current?.stop();
      setIsRecording(false);
      return;
    }

    try {
      const flux = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(flux);
      const morceaux: BlobPart[] = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) morceaux.push(e.data);
      };
      recorder.onstop = () => {
        flux.getTracks().forEach((piste) => piste.stop());
        const blob = new Blob(morceaux, { type: recorder.mimeType || 'audio/webm' });
        if (blob.size > 0) envoyerMessageVocal(blob);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch {
      setError(t('jarvis.mic_error'));
    }
  };

  const messagesAffiches = messages.length > 0 ? messages : [messageAccueil];
  const enCours = isSending || isTranscribing;

  return (
    <div id="jarvis-widget" className="bg-gradient-to-b from-secondary/10 via-card to-card rounded-2xl border border-secondary/30 p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-secondary text-secondary-foreground shadow-sm">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
              <span>JARVIS IA</span>
              <span className="text-[10px] bg-secondary/20 text-secondary px-1.5 py-0.2 rounded font-black uppercase">{t('jarvis.active')}</span>
            </h3>
            <p className="text-[11px] text-muted-foreground">{t('jarvis.tagline')}</p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 relative" ref={historiqueRef}>
          <button
            onClick={demarrerNouvelleConversation}
            title={t('jarvis.new_conversation')}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <Plus className="h-4 w-4" />
          </button>
          <button
            onClick={() => setAfficherHistorique((prev) => !prev)}
            title={t('jarvis.conversation_history')}
            className="p-1.5 rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <History className="h-4 w-4" />
          </button>

          {afficherHistorique && (
            <div className="absolute right-0 top-full mt-2 w-64 max-w-[80vw] bg-card border border-border rounded-2xl shadow-2xl z-50 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
              <div className="p-3 border-b border-border bg-muted/40">
                <h4 className="text-xs font-bold text-foreground">{t('jarvis.conversations')}</h4>
              </div>
              <div className="max-h-64 overflow-y-auto divide-y divide-border">
                {conversations.length === 0 ? (
                  <p className="text-[11px] text-muted-foreground text-center py-6">{t('jarvis.none_yet')}</p>
                ) : (
                  conversations.map((conv) => (
                    <button
                      key={conv.id_conversation}
                      onClick={() => ouvrirConversation(conv.id_conversation)}
                      className={`w-full text-left p-3 flex items-center justify-between gap-2 hover:bg-muted/40 transition-colors ${
                        conv.id_conversation === conversationActuelle ? 'bg-secondary/10' : ''
                      }`}
                    >
                      <div className="min-w-0">
                        <p className="text-[11px] font-bold text-foreground truncate">{conv.titre || t('jarvis.new_conversation')}</p>
                        <p className="text-[10px] text-muted-foreground">{formatDateRelative(conv.date_dernier_message)}</p>
                      </div>
                      <span
                        role="button"
                        onClick={(e) => supprimerConversation(e, conv.id_conversation)}
                        className="p-1 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive shrink-0"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </span>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {error && (
        <p className="text-[11px] text-destructive flex items-center gap-1.5">
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          <span>{error}</span>
        </p>
      )}

      <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
        {isLoadingConversation ? (
          <div className="flex justify-center py-6">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          messagesAffiches.map((msg) => (
            <div key={msg.id_message} className={`flex ${msg.type === 'QUESTION' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[85%] p-3 rounded-2xl text-xs leading-relaxed space-y-1 ${
                  msg.type === 'QUESTION'
                    ? 'bg-secondary text-secondary-foreground font-semibold rounded-tr-none'
                    : 'bg-muted text-foreground border border-border/60 rounded-tl-none'
                }`}
              >
                <div className="flex items-start gap-1.5">
                  {msg.canal === 'VOCAL' && <Volume2 className="h-3 w-3 mt-0.5 shrink-0 opacity-70" />}
                  <span>{msg.contenu}</span>
                </div>
                {msg.conseil_supplementaire && (
                  <p className="text-[11px] italic opacity-80 pt-1 border-t border-border/40">{msg.conseil_supplementaire}</p>
                )}
                {msg.actions.length > 0 && (
                  <div className="space-y-1.5 pt-1.5 mt-1 border-t border-border/40">
                    {msg.actions.map((action) => (
                      <div key={action.id_action} className="bg-background/70 border border-border/60 rounded-xl p-2 space-y-1.5">
                        <div className="flex items-start gap-1.5">
                          <Sparkles className="h-3 w-3 mt-0.5 shrink-0 text-secondary" />
                          <span className="text-[11px] font-semibold">{action.resume}</span>
                        </div>
                        {action.statut === 'EN_ATTENTE' ? (
                          <div className="flex gap-1.5">
                            <button
                              type="button"
                              onClick={() => traiterAction(action.id_action, 'confirmer')}
                              disabled={actionsEnCours.has(action.id_action)}
                              className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-secondary text-secondary-foreground text-[11px] font-bold hover:bg-secondary/90 disabled:opacity-60"
                            >
                              {actionsEnCours.has(action.id_action) ? (
                                <Loader2 className="h-3 w-3 animate-spin" />
                              ) : (
                                <CheckCircle2 className="h-3 w-3" />
                              )}
                              <span>{t('jarvis.action_confirm')}</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => traiterAction(action.id_action, 'annuler')}
                              disabled={actionsEnCours.has(action.id_action)}
                              className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-lg bg-muted text-muted-foreground text-[11px] font-bold hover:bg-accent disabled:opacity-60"
                            >
                              <Ban className="h-3 w-3" />
                              <span>{t('jarvis.action_cancel')}</span>
                            </button>
                          </div>
                        ) : (
                          <p className={`text-[11px] font-bold flex items-center gap-1 ${action.statut === 'EXECUTE' ? 'text-forest-600 dark:text-forest-400' : 'text-muted-foreground'}`}>
                            {action.statut === 'EXECUTE' ? <CheckCircle2 className="h-3 w-3" /> : <Ban className="h-3 w-3" />}
                            <span>{action.statut === 'EXECUTE' ? t('jarvis.action_executed') : t('jarvis.action_cancelled')}</span>
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {enCours && (
          <div className="flex justify-start">
            <div className="p-3 rounded-2xl bg-muted border border-border/60 rounded-tl-none">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}
      </div>

      <form onSubmit={envoyerMessageTexte} className="relative flex items-center gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            placeholder={isRecording ? t('jarvis.recording') : t('jarvis.ask_placeholder')}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={enCours || isRecording}
            className="w-full bg-background border border-border rounded-xl px-3.5 py-2.5 text-xs pr-10 focus:outline-none focus:ring-2 focus:ring-secondary disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={enCours || isRecording || !query.trim()}
            className="absolute right-2 top-2 p-1.5 rounded-lg bg-secondary text-secondary-foreground hover:bg-secondary/90 transition-colors disabled:opacity-60"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>

        <button
          type="button"
          onClick={basculerEnregistrement}
          disabled={enCours}
          title={isRecording ? t('jarvis.stop_recording') : t('jarvis.ask_by_voice')}
          className={`p-2.5 rounded-xl transition-colors shrink-0 disabled:opacity-60 ${
            isRecording
              ? 'bg-destructive text-destructive-foreground animate-pulse'
              : 'bg-muted text-muted-foreground hover:text-foreground hover:bg-accent'
          }`}
        >
          {isRecording ? <Square className="h-3.5 w-3.5" /> : <Mic className="h-3.5 w-3.5" />}
        </button>
      </form>
    </div>
  );
};
