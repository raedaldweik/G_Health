import { useApp } from '../context/AppContext';

const PILLARS = [
  { title: 'Multi-agent orchestration', icon: '◈', text: 'A Gemini supervisor routes work to five specialists — every hop visible in the trace.' },
  { title: 'Grounded RAG', icon: '📖', text: 'Answers cite national clinical guidelines — document and page. No memory, no hallucination.' },
  { title: 'Real machine learning', icon: '⚡', text: 'Four deployed models: XGBoost risk (AUC 0.85), segments, similarity, demand forecast.' },
  { title: 'Population-health MCP ★', icon: '🔌', text: 'The first population-health MCP server on Google Cloud — measures, gaps, cohorts, counterfactuals.' },
  { title: 'Counterfactual simulation', icon: '∿', text: 'Policy what-ifs by re-scoring the cohort through the model — never a canned number.' },
  { title: 'Human-in-the-loop', icon: '✓', text: 'Agents draft; clinicians sign. Consent enforced, every action audited.' },
];

export default function LandingPage({ go }) {
  const { personaInfo } = useApp();
  return (
    <div className="h-full overflow-y-auto flex items-center justify-center p-8">
      <div className="max-w-[860px] text-center animate-fade-up">
        <h1 className="text-[30px] font-extrabold tracking-tight leading-tight mb-4" style={{ color: 'var(--text)' }}>
          The nation's pulse, <span style={{ color: 'var(--brand)' }}>made intelligible.</span>
        </h1>

        <p className="text-[14px] leading-relaxed max-w-[640px] mx-auto mb-2" style={{ color: 'var(--text-md)' }}>
          An agentic AI layer on top of the national Health Information Exchange — a
          <b> 4,000-patient cardiometabolic registry</b> with 36 months of longitudinal, coded records.
          It answers clinical and executive questions by querying the HIE, grounding in national
          guidelines, scoring deployed ML models, and drafting actions a human signs.
        </p>
        <p className="text-[11px] mb-7" style={{ color: 'var(--text-faint)' }}>
          Built for Google Cloud: Gemini · Agent Development Kit · Model Context Protocol · target region me-central1 (Doha) · all data synthetic
        </p>

        <div className="grid grid-cols-3 gap-3 mb-8 text-left">
          {PILLARS.map((p) => (
            <div key={p.title} className="glass-card p-4">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[15px]">{p.icon}</span>
                <p className="text-[12px] font-bold" style={{ color: 'var(--text)' }}>{p.title}</p>
              </div>
              <p className="text-[10.5px] leading-relaxed" style={{ color: 'var(--text-dim)' }}>{p.text}</p>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-center gap-3">
          <button onClick={() => go('assistant')}
            className="px-6 py-3 rounded-xl text-[13px] font-bold text-white transition-all hover:scale-[1.03]"
            style={{ background: 'var(--brand-grad)', boxShadow: '0 6px 20px rgba(26,115,232,0.35)' }}>
            Open the Assistant →
          </button>
          <button onClick={() => go('overview')}
            className="px-6 py-3 rounded-xl text-[13px] font-bold transition-all hover:scale-[1.03]"
            style={{ background: 'var(--glass-strong)', color: 'var(--brand-lo)', border: '1px solid rgba(26,115,232,0.25)' }}>
            View the dashboards
          </button>
        </div>
        <p className="text-[10.5px] mt-4" style={{ color: 'var(--text-faint)' }}>
          Signed in as {personaInfo.name} — switch persona top-right to change the experience.
        </p>
      </div>
    </div>
  );
}
