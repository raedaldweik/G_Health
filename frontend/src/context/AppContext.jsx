import { createContext, useContext, useState } from 'react';

export const PERSONAS = {
  clinician: {
    id: 'clinician', name: 'Dr. Amal Al-Mansoori', sub: 'Consultant Endocrinologist',
    avatar: 'AM', color: 'bg-teal-700',
  },
  executive: {
    id: 'executive', name: 'Dr. Khalid Al-Kuwari', sub: 'Population Health Executive',
    avatar: 'KK', color: 'bg-blue-800',
  },
};

const Ctx = createContext(null);

const newSession = () => `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;

export function AppProvider({ children }) {
  const [persona, setPersona] = useState('clinician');
  const [messages, setMessages] = useState([]);      // chat transcript
  const [sessionId, setSessionId] = useState(newSession);

  const addMessage = (m) => setMessages((prev) => [...prev, m]);
  const patchLastMessage = (patch) =>
    setMessages((prev) => prev.map((m, i) => (i === prev.length - 1 ? { ...m, ...patch } : m)));
  const resetChat = () => { setMessages([]); setSessionId(newSession()); };

  return (
    <Ctx.Provider value={{
      persona, setPersona, personaInfo: PERSONAS[persona],
      messages, addMessage, patchLastMessage, resetChat, sessionId,
    }}>
      {children}
    </Ctx.Provider>
  );
}

export const useApp = () => useContext(Ctx);
