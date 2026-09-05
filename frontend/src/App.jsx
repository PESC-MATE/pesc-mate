import { useEffect, useState } from "react";

import { getHealth } from "./services/api";

function App() {
  const [serverStatus, setServerStatus] = useState("확인 중");

  useEffect(() => {
    getHealth()
      .then(() => setServerStatus("연결됨"))
      .catch(() => setServerStatus("연결 안 됨"));
  }, []);

  return (
    <main className="app">
      <section className="welcome">
        <p className="eyebrow">AI 기반 PECS 의사소통 플랫폼</p>
        <h1>PESC MATE</h1>
        <p>그림 카드를 선택해 나만의 문장을 만들어 보세요.</p>
        <span className="status">API 서버: {serverStatus}</span>
      </section>
    </main>
  );
}

export default App;
