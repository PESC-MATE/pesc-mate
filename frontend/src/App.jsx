import { useEffect, useState } from "react";

import { hasToken, request, setToken } from "./services/api";

function App() {
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [username, setUsername] = useState('demo');
  const [password, setPassword] = useState('demo1234');
  const [cards, setCards] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [board, setBoard] = useState([]);
  const [category, setCategory] = useState('전체');
  const [search, setSearch] = useState('');
  const [tab, setTab] = useState('cards');
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [stats, setStats] = useState(null);
  const [speaking, setSpeaking] = useState(false);
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());

  async function load() {
    setError('');
    try {
      const [all, rec, dashboard] = await Promise.all([request('/cards'), request('/recommendations'), request('/dashboard')]);
      setCards(all); setRecommended(rec); setStats(dashboard); setLoaded(true);
    } catch (e) {
      if (e.status === 401) { setToken(null); setUser(null); setLoaded(false); setError('로그인이 만료되었습니다. 다시 로그인해 주세요.'); }
      else setError(e.message || '서버에 연결하지 못했습니다.');
    }
  }
  useEffect(() => {
    async function restoreLogin() {
      if (!hasToken()) { setAuthReady(true); return; }
      try {
        const account = await request('/auth/me');
        setUser(account);
        await load();
      } catch { setToken(null); }
      finally { setAuthReady(true); }
    }
    restoreLogin();
    return () => window.speechSynthesis?.cancel();
  }, []);

  async function handleLogin(event) {
    event.preventDefault(); setBusy(true); setError('');
    try {
      const result = await request('/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) });
      setToken(result.access_token); setUser(result.user);
      await load();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); setAuthReady(true); }
  }

  async function handleLogout() {
    setBusy(true);
    try { await request('/auth/logout', { method: 'POST' }); } catch { /* local logout still applies */ }
    window.speechSynthesis?.cancel(); setToken(null); setUser(null); setLoaded(false);
    setCards([]); setRecommended([]); setStats(null); setBoard([]); setText(''); setError(''); setBusy(false);
  }

  function updateBoard(next) {
    window.speechSynthesis?.cancel(); setSpeaking(false);
    setBoard(next); setText(''); setRequestId(crypto.randomUUID());
  }
  function add(card) {
    if (board.length >= 12) { setError('카드는 최대 12장까지 선택할 수 있어요.'); return; }
    setError(''); updateBoard([...board, card]);
  }
  function move(index, offset) {
    const next = [...board];
    [next[index], next[index + offset]] = [next[index + offset], next[index]];
    updateBoard(next);
  }
  async function generate() {
    setBusy(true); setError('');
    try {
      const result = await request('/sentences', { method: 'POST', body: JSON.stringify({ cards: board.map(c => c.id), request_id: requestId }) });
      setText(result.sentence);
      try {
        const [rec, dashboard] = await Promise.all([request('/recommendations'), request('/dashboard')]);
        setRecommended(rec); setStats(dashboard);
      } catch { setError('문장은 저장되었습니다. 통계 갱신은 다시 연결을 눌러 주세요.'); }
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }
  function speak() {
    if (!window.speechSynthesis) { setError('이 브라우저는 음성 출력을 지원하지 않습니다.'); return; }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'ko-KR'; utterance.rate = 0.85;
    const voice = window.speechSynthesis.getVoices().find(v => v.lang.startsWith('ko'));
    if (voice) utterance.voice = voice;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = (event) => { setSpeaking(false); if (!['canceled', 'interrupted'].includes(event.error)) setError('음성을 재생하지 못했습니다. 기기의 한국어 음성 설정을 확인해 주세요.'); };
    setSpeaking(true); window.speechSynthesis.speak(utterance);
  }
  function tile(card) {
    return <button className="card" key={card.id} disabled={busy} onClick={() => add(card)}><span aria-hidden="true">{card.symbol}</span>{card.label}</button>;
  }
  if (!authReady) return <main className="login-page"><p role="status">로그인 정보를 확인하는 중입니다…</p></main>;
  if (!user) return <main className="login-page"><section className="login-card">
    <div className="login-mascot" aria-hidden="true">💬</div><p className="eyebrow">그림으로 전하는 나의 이야기</p><h1>PESC MATE</h1>
    <h2>로그인</h2><p className="muted">내 카드 기록과 추천을 불러옵니다.</p>
    {error && <div role="alert" className="error">{error}</div>}
    <form onSubmit={handleLogin}>
      <label>아이디<input autoFocus autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required maxLength="64" /></label>
      <label>비밀번호<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} required maxLength="128" /></label>
      <button className="primary full" disabled={busy}>{busy ? '로그인 중…' : '로그인'}</button>
    </form><p className="demo-account">데모 계정: <code>demo</code> / <code>demo1234</code></p>
  </section></main>;
  return <main className="app">
    <header><div className="brand"><span className="brand-mark" aria-hidden="true">💬</span><div><p className="eyebrow">그림으로 전하는 나의 이야기</p><h1>PESC MATE</h1></div></div><div className="account"><span className="profile-avatar" aria-hidden="true">😊</span><span className="status">{user.name} · {loaded ? '연결됨' : '연결 대기'}</span><button onClick={handleLogout} disabled={busy}>로그아웃</button></div></header>
    <nav aria-label="주 메뉴"><button className={tab === 'cards' ? 'active' : ''} onClick={() => setTab('cards')}><span aria-hidden="true">🖼️</span>그림으로 말하기</button><button className={tab === 'dashboard' ? 'active' : ''} onClick={() => setTab('dashboard')}><span aria-hidden="true">📊</span>이용 현황</button></nav>
    {error && <div role="alert" className="error">{error} <button disabled={busy} onClick={load}>다시 연결</button></div>}
    {!loaded && !error && <p role="status">카드를 불러오는 중입니다…</p>}
    {tab === 'cards' ? <div className="communication-layout">
      <section className="recommend-panel"><div className="panel-heading"><span aria-hidden="true">⭐</span><div><h2>자주 쓰는 카드</h2><p className="muted">나를 위한 추천</p></div></div><div className="cards recommendations">{recommended.map(tile)}</div></section>
      <div className="workspace"><section><div className="section-title"><h2>무엇을 말하고 싶나요?</h2><input aria-label="카드 검색" placeholder="카드 이름 검색" value={search} onChange={e => setSearch(e.target.value)} /></div>
        <div className="categories" aria-label="카테고리">{['전체', ...new Set(cards.map(c => c.category))].map(c => <button key={c} aria-pressed={category === c} className={category === c ? 'active' : ''} onClick={() => setCategory(c)}>{c}</button>)}</div>
        <div className="cards">{cards.filter(c => (category === '전체' || c.category === category) && c.label.includes(search.trim())).map(tile)}</div>
        {loaded && !cards.some(c => (category === '전체' || c.category === category) && c.label.includes(search.trim())) && <p>검색 결과가 없어요.</p>}
      </section>
      <section className="board"><div className="section-title"><h2>나의 문장 <small>{board.length}/12</small></h2><button disabled={!board.length || busy} onClick={() => { if (window.confirm('선택한 카드를 모두 지울까요?')) updateBoard([]); }}>비우기</button></div>
        {!board.length && <p className="empty">왼쪽 카드를 눌러 보세요.<br />나 → 물 → 마시다</p>}
        <ol>{board.map((c, i) => <li key={`${c.id}-${i}`}><span>{c.symbol} {c.label}</span><div><button aria-label={`${i + 1}번째 카드 앞으로`} disabled={i === 0 || busy} onClick={() => move(i, -1)}>←</button><button aria-label={`${i + 1}번째 카드 뒤로`} disabled={i === board.length - 1 || busy} onClick={() => move(i, 1)}>→</button><button aria-label={`${i + 1}번째 카드 삭제`} disabled={busy} onClick={() => updateBoard(board.filter((_, n) => n !== i))}>×</button></div></li>)}</ol>
        <button className="primary full" disabled={!board.length || busy} onClick={generate}>{busy ? '문장을 만드는 중…' : '문장 만들기 · 저장'}</button>
        <div className="sentence" aria-live="polite">{text || '만든 문장이 여기에 표시돼요.'}</div>
        <div className="actions"><button className="primary" disabled={!text || busy || speaking} onClick={speak}>🔊 읽어주기</button><button disabled={!speaking} onClick={() => { window.speechSynthesis.cancel(); setSpeaking(false); }}>중지</button></div>
        <p className="muted">현재는 규칙 기반 문장 생성을 사용합니다. 지원하지 않는 조합은 선택한 단어를 순서대로 표시합니다.</p>
      </section></div>
    </div> : <section className="dashboard"><div className="panel-heading"><span aria-hidden="true">🏆</span><div><h2>나의 의사소통 기록</h2><p className="muted">{user.name} · 전체 기간 · 문장 저장 기준 (개별 클릭은 집계하지 않음)</p></div></div>
      {stats && <><div className="metrics"><div>저장한 문장<strong>{stats.sessions}개</strong></div><div>사용한 카드<strong>{stats.selections}장</strong></div></div>
        <h3>카테고리별 사용</h3>{Object.entries(stats.categories).map(([name, count]) => <div className="bar" key={name}><span>{name}</span><meter min="0" max={Math.max(stats.selections, 1)} value={count} /> {count}회</div>)}
        <h3>자주 사용한 카드</h3><div className="categories">{stats.top_cards.slice(0, 8).map(c => <span className="status" key={c.id}>{c.symbol} {c.label} · {c.count}회</span>)}</div>
        <h3>최근 문장</h3>{!stats.recent.length ? <p className="empty">아직 기록이 없어요. 첫 문장을 만들어 보세요.</p> : <ul className="history">{stats.recent.map(r => <li key={r.id}><span>{r.sentence}</span><time>{new Date(r.created_at).toLocaleString('ko-KR')}</time></li>)}</ul>}</>}
    </section>}
    <footer>실행용 프로토타입 · 실제 개인정보를 입력하지 마세요.</footer>
  </main>;
}

export default App;
