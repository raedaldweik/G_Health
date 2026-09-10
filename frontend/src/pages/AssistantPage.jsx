import { useEffect, useRef, useState } from 'react';
import { useApp } from '../context/AppContext';
import { getScenarios, streamChat } from '../services/api';
import ResponseCard from '../components/ResponseCard';
import SourceViewer from '../components/SourceViewer';
import DetailsPopup from '../components/DetailsPopup';
import { VoiceInput, SpeakerToggle, useSpeaker } from '../components/VoiceControls';
import { AgentChip } from '../components/ui';

export default function AssistantPage() {
  const {
    persona, personaInfo, chats, activeChat, activeChatId,
    setActiveChatId, createNewChat, addMessage, renameChat, deleteChat,
  } = useApp();
  const messages = activeChat?.messages || [];

  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [liveSteps, setLiveSteps] = useState([]);
  const [draft, setDraft] = useState('');   // supervisor prose streamed token-by-token
  const [scenarios, setScenarios] = useState([]);
  const [llmInfo, setLlmInfo] = useState(null);
  const [source, setSource] = useState(null);
  const [details, setDetails] = useState(null);
  const [voiceLang, setVoiceLang] = useState('en');
  const [chatMenu, setChatMenu] = useState(null);
  const [renaming, setRenaming] = useState(null);
  const [renameValue, setRenameValue] = useState('');
  const speaker = useSpeaker();
  const inputRef = useRef(null);
  const endRef = useRef(null);

  useEffect(() => {
    getScenarios(persona).then((r) => {
      setScenarios(r.scenarios || []);
      setLlmInfo({ enabled: r.llm_enabled, model: r.model });
    }).catch(() => setScenarios([]));
  }, [persona]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, liveSteps, loading, draft]);

  const send = async (text, scenarioId = null) => {
    const q = (text || input).trim();
    if (!q || loading || !activeChat) return;
    const chatId = activeChat.id;
    setInput('');
    addMessage(chatId, { role: 'user', content: q });
    setLoading(true);
    setLiveSteps([]);
    setDraft('');
    try {
      let finalData = null;
      await streamChat({ message: q, sessionId: chatId, persona, scenarioId }, (ev) => {
        if (ev.type === 'step') setLiveSteps((prev) => [...prev, ev]);
        else if (ev.type === 'delta') setDraft((prev) => prev + ev.text);
        else if (ev.type === 'reset') { setDraft(''); setLiveSteps([]); }
        else if (ev.type === 'final') finalData = ev;
      });
      if (finalData) {
        addMessage(chatId, { role: 'assistant', data: finalData, query: q });
        speaker.speak(finalData.answer);
      } else {
        addMessage(chatId, { role: 'assistant', error: 'The stream ended without an answer. Try again.' });
      }
    } catch (e) {
      addMessage(chatId, { role: 'assistant', error: `Connection error: ${e.message}` });
    }
    setLoading(false);
    setLiveSteps([]);
    setDraft('');
    inputRef.current?.focus();
  };

  const startRename = (chat) => { setRenaming(chat.id); setRenameValue(chat.title); setChatMenu(null); };
  const finishRename = (id) => { if (renameValue.trim()) renameChat(id, renameValue.trim()); setRenaming(null); };

  const liveVisible = liveSteps.filter((s) => s.status === 'done').slice(-6);

  return (
    <div className="h-full flex gap-4 p-4 pt-3">

      {/* Left rail, Recent conversations (Roads recipe) + agent system */}
      <div className="w-[262px] shrink-0 flex flex-col gap-3 min-h-0">
        <div className="glass-card flex flex-col flex-1 min-h-0">
          <div className="p-4 border-b border-[rgba(15,23,42,0.07)]">
            <p className="panel-title">Recent conversations</p>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {chats.map((chat) => {
              const isRenaming = renaming === chat.id;
              const menuOpen = chatMenu === chat.id;
              return (
                <div key={chat.id} className="relative group">
                  {isRenaming ? (
                    <div className="px-2 py-1.5">
                      <input value={renameValue} onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => finishRename(chat.id)}
                        onKeyDown={(e) => e.key === 'Enter' && finishRename(chat.id)} autoFocus
                        className="w-full rounded-lg px-2 py-1.5 text-xs border outline-none"
                        style={{ background: 'rgba(255,255,255,0.5)', borderColor: 'var(--brand-hi)', color: 'var(--text)' }} />
                    </div>
                  ) : (
                    <div className="flex items-center">
                      <button onClick={() => setActiveChatId(chat.id)}
                        className={`flex-1 flex items-center gap-2 px-3 py-2.5 rounded-lg text-xs text-left truncate transition-all ${
                          chat.id === activeChatId ? 'font-semibold' : 'hover:bg-[rgba(138,21,56,0.05)] border border-transparent'
                        }`}
                        style={chat.id === activeChatId
                          ? { color: 'var(--brand-lo)', background: 'rgba(138,21,56,0.14)', border: '1px solid rgba(138,21,56,0.30)', borderLeft: '3px solid var(--brand)' }
                          : { color: 'var(--text-md)' }}>
                        <span className="text-sm">💬</span>
                        <span className="truncate flex-1">{chat.title}</span>
                      </button>
                      <button onClick={(e) => { e.stopPropagation(); setChatMenu(menuOpen ? null : chat.id); }}
                        className="p-1 rounded-md opacity-0 group-hover:opacity-100 hover:bg-[rgba(138,21,56,0.1)] transition-all shrink-0 ml-0.5"
                        style={{ color: 'var(--text-faint)' }}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <circle cx="12" cy="5" r="1" /><circle cx="12" cy="12" r="1" /><circle cx="12" cy="19" r="1" />
                        </svg>
                      </button>
                    </div>
                  )}
                  {menuOpen && (
                    <>
                      <div className="fixed inset-0 z-40" onClick={() => setChatMenu(null)} />
                      <div className="absolute right-0 top-full mt-0.5 rounded-xl shadow-xl overflow-hidden z-50 min-w-[130px] animate-fade-up"
                        style={{ background: 'rgba(255,255,255,0.96)', border: '1px solid rgba(138,21,56,0.2)', backdropFilter: 'blur(20px)' }}>
                        <button onClick={() => startRename(chat)}
                          className="w-full flex items-center gap-2 px-3 py-2 text-[11px] hover:bg-[rgba(138,21,56,0.05)]"
                          style={{ color: 'var(--text-md)' }}>
                          Rename
                        </button>
                        <button onClick={() => { setChatMenu(null); deleteChat(chat.id); }}
                          className="w-full flex items-center gap-2 px-3 py-2 text-[11px] hover:bg-[var(--red-bg)]"
                          style={{ color: 'var(--red)' }}>
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })}
          </div>
          <div className="p-3 border-t border-[rgba(15,23,42,0.07)]">
            <button onClick={createNewChat}
              className="w-full py-2.5 rounded-lg text-xs font-bold transition-all"
              style={{ border: '2px dashed rgba(138,21,56,0.35)', color: 'var(--brand)', background: 'rgba(138,21,56,0.03)' }}>
              + New conversation
            </button>
          </div>
        </div>

        {/* Compact agent roster */}
        <div className="glass-card p-3.5 shrink-0">
          <p className="panel-title mb-2.5">Agent system</p>
          <div className="flex flex-wrap gap-1.5">
            {['nabd_supervisor', 'cohort_agent', 'guideline_agent', 'risk_agent', 'pophealth_agent', 'action_agent']
              .map((a) => <AgentChip key={a} agent={a} />)}
          </div>
          <p className="text-[9.5px] mt-2 leading-snug" style={{ color: 'var(--text-faint)' }}>
            {llmInfo?.enabled
              ? <>Live multi-agent · <b style={{ color: 'var(--text-dim)' }}>function-calling supervisor</b> · MCP over stdio</>
              : <>Direct tool runs on live data. Free-form chat needs the model credentials on the server</>}
          </p>
        </div>
      </div>

      {/* Main chat card */}
      <div className="flex-1 glass-card flex flex-col relative min-w-0" style={{ boxShadow: 'var(--glass-shadow-lg)' }}>
        <img src="/nabd-mark.svg" alt="" className="chat-watermark" />

        <div className="flex items-center justify-between px-6 py-3 border-b border-[rgba(15,23,42,0.07)] relative z-[5]">
          <div className="flex items-center gap-2 min-w-0">
            <span className="w-[3px] h-4 rounded shrink-0" style={{ background: 'var(--brand-grad)' }} />
            <span className="text-sm font-bold truncate" style={{ color: 'var(--text)' }}>
              {activeChat?.title || 'New conversation'}
            </span>
          </div>
          <span className="text-[10.5px] px-2 py-0.5 rounded-full font-semibold shrink-0"
            style={{ background: 'rgba(138,21,56,0.08)', color: 'var(--brand-lo)' }}>
            {personaInfo.sub}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5 relative z-[1]">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-2.5 animate-fade-up ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
              {msg.role === 'user' ? (
                <div className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center text-[10px] font-bold text-white ${personaInfo.color}`}>
                  {personaInfo.avatar}
                </div>
              ) : (
                <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center p-1"
                  style={{ background: 'rgba(255,255,255,0.92)', border: '1px solid rgba(15,23,42,0.10)', boxShadow: '0 1px 3px rgba(15,23,42,0.08)' }}>
                  <img src="/nabd-mark.svg" alt="Nabd" className="w-full h-full object-contain" />
                </div>
              )}
              <div className="max-w-[78%] min-w-0">
                {msg.role === 'user' ? (
                  <div className="msg-user-bubble px-4 py-3 text-[13px] leading-[1.75]" style={{ color: 'var(--text)' }}>
                    {msg.content}
                  </div>
                ) : msg.error ? (
                  <div className="msg-bot-bubble px-4 py-3 text-[13px]" style={{ color: 'var(--red)' }}>{msg.error}</div>
                ) : msg.welcome ? (
                  <div className="msg-bot-bubble px-4 py-3 text-[13px] leading-[1.75]" style={{ color: 'var(--text)' }}>
                    {msg.content}
                  </div>
                ) : (
                  <ResponseCard data={msg.data}
                    onOpenSource={setSource}
                    onOpenDetails={(d) => setDetails({ data: d, query: msg.query })} />
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-2.5 animate-fade-up">
              <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center p-1"
                style={{ background: 'rgba(255,255,255,0.92)', border: '1px solid rgba(15,23,42,0.10)', boxShadow: '0 1px 3px rgba(15,23,42,0.08)' }}>
                <img src="/nabd-mark.svg" alt="" className="w-full h-full object-contain" />
              </div>
              <div className="msg-bot-bubble px-4 py-3 min-w-[240px]">
                {liveVisible.length > 0 && (
                  <div className="mb-2.5 space-y-1.5">
                    {liveVisible.map((s, i, arr) => (
                      <div key={i} className="flex items-center gap-2 text-[11.5px] animate-fade-up"
                        style={{ color: i === arr.length - 1 ? 'var(--brand-lo)' : 'var(--text-dim)' }}>
                        <AgentChip agent={s.agent} />
                        <span className="truncate font-mono text-[10.5px]">{s.tool}</span>
                        <span className="truncate text-[10.5px] flex-1">{s.detail}</span>
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="var(--green)" strokeWidth="3" className="shrink-0">
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      </div>
                    ))}
                  </div>
                )}
                {draft && (
                  <div className="mb-2 text-[13px] leading-[1.7] whitespace-pre-wrap" style={{ color: 'var(--text)' }}>
                    {draft.replace(/[*#`]/g, '')}<span className="inline-block w-1.5 h-3.5 ml-0.5 align-middle animate-pulse" style={{ background: 'var(--brand)' }} />
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <div className="flex gap-1.5">
                    {[0, 1, 2].map((j) => (
                      <span key={j} className="w-1.5 h-1.5 rounded-full"
                        style={{ background: 'var(--brand)', opacity: 0.3, animation: `pop 1.4s ease-in-out infinite ${j * 0.15}s` }} />
                    ))}
                  </div>
                  <span className="text-[10px]" style={{ color: 'var(--text-faint)' }}>
                    {draft ? 'writing…'
                      : liveSteps.filter((s) => s.status === 'done').length > 0
                      ? `${liveSteps.filter((s) => s.status === 'done').length} agent steps so far`
                      : 'agents working…'}
                  </span>
                </div>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Scenario chips + input bar */}
        <div className="px-5 pb-4 pt-1 relative z-[1]">
          {scenarios.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {scenarios.map((s) => (
                <button key={s.id} className="suggestion-chip" disabled={loading}
                  onClick={() => send(s.question, s.id)}>
                  <span className="chip-tag">{s.tag}</span>
                  {s.label}
                </button>
              ))}
            </div>
          )}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-xl border border-[rgba(15,23,42,0.10)] transition-all focus-within:border-[var(--brand-hi)] focus-within:shadow-[0_0_0_3px_rgba(138,21,56,0.10)]"
            style={{ background: 'var(--glass-strong)', backdropFilter: 'blur(12px)' }}>
            <VoiceInput onTranscript={(t) => send(t)} disabled={loading} lang={voiceLang} />
            <button onClick={() => setVoiceLang(voiceLang === 'en' ? 'ar' : 'en')}
              title="Toggle voice language (English / العربية)"
              className="h-8 px-1.5 rounded-lg text-[10px] font-bold shrink-0 transition-all hover:bg-[rgba(138,21,56,0.08)]"
              style={{ color: 'var(--text-dim)' }}>
              {voiceLang === 'en' ? 'EN' : 'ع'}
            </button>
            <SpeakerToggle speaker={speaker} />
            <textarea ref={inputRef} rows="1" value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              placeholder={`Ask about the ${persona === 'clinician' ? 'panel' : 'population'}: data, guidelines, risk, what-ifs`}
              className="flex-1 bg-transparent border-none outline-none text-[13px] py-2 px-2 resize-none leading-relaxed"
              style={{ fontFamily: 'Manrope, sans-serif', color: 'var(--text)' }} />
            <button onClick={() => send()}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-white shrink-0 hover:scale-105 transition-transform"
              style={{ background: 'var(--brand-grad)', boxShadow: '0 3px 12px rgba(138,21,56,0.30)' }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {source && <SourceViewer source={source} onClose={() => setSource(null)} />}
      {details && (
        <DetailsPopup data={details.data} query={details.query}
          onClose={() => setDetails(null)} onOpenSource={setSource} />
      )}
    </div>
  );
}
