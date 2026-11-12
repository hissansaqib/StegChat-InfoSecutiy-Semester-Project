// src/contexts/CryptoContext.tsx
import React, { createContext, useState, useEffect, useCallback, ReactNode } from "react";
import { CryptoKey, CryptoKeyPair } from "../crypto/keyVault"; // Types are global, but we just import for TS compatibility.

interface CryptoState {
  masterKey?: CryptoKey;
  ecdhKeyPair?: CryptoKeyPair;
  locked: boolean;
  lock: () => void;
  unlock: (master: CryptoKey, pair: CryptoKeyPair) => void;
}

export const CryptoContext = createContext<CryptoState>({
  locked: true,
  lock: () => {},
  unlock: () => {},
});

export const CryptoProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [masterKey, setMasterKey] = useState<CryptoKey>();
  const [ecdhKeyPair, setEcdhKeyPair] = useState<CryptoKeyPair>();
  const [locked, setLocked] = useState(true);

  const lock = useCallback(() => {
    setMasterKey(undefined);
    setEcdhKeyPair(undefined);
    setLocked(true);
  }, []);

  const unlock = useCallback((mk: CryptoKey, kp: CryptoKeyPair) => {
    setMasterKey(mk);
    setEcdhKeyPair(kp);
    setLocked(false);
  }, []);

  // Auto‑lock after inactivity (default 5 min). Reset on user activity.
  useEffect(() => {
    let timer: NodeJS.Timeout;
    const reset = () => {
      clearTimeout(timer);
      timer = setTimeout(lock, 5 * 60 * 1000);
    };
    window.addEventListener("mousemove", reset);
    window.addEventListener("keydown", reset);
    reset();
    return () => {
      clearTimeout(timer);
      window.removeEventListener("mousemove", reset);
      window.removeEventListener("keydown", reset);
    };
  }, [lock]);

  // TODO: integrate with AuthContext logout to call lock().

  return (
    <CryptoContext.Provider value={{ masterKey, ecdhKeyPair, locked, lock, unlock }}>
      {children}
    </CryptoContext.Provider>
  );
};

