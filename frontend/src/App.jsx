import { useEffect, useState } from "react";

import { hasToken, request, requestBlob, setToken } from "./services/api";
import { clearBoard, loadBoard, saveBoard } from "./services/boardStorage";
import cardSprite from "./assets/cards/pecs-card-sprite.png";

const CARD_META = Object.fromEntries([
  ['me', '나'], ['mom', '엄마'], ['water', '물'], ['rice', '밥'], ['apple', '사과'], ['milk', '우유'],
  ['drink', '마시다'], ['eat', '먹다'], ['go', '가다'], ['rest', '쉬다'], ['play', '놀다'], ['help', '도와주세요'],
  ['toilet', '화장실'], ['home', '집'], ['happy', '좋아요'], ['hurt', '아파요'], ['no', '싫어요'], ['yes', '네'],
].map(([id, label], image_index) => [id, { id, label, image_index }]));

function App() {
  const [user, setUser] = useState(null);
  const [authReady, setAuthReady] = useState(false);
  const [username, setUsername] = useState('demo');
  const [password, setPassword] = useState('demo1234');
  const [authMode, setAuthMode] = useState('login');
  const [name, setName] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [cards, setCards] = useState([]);
  const [recommended, setRecommended] = useState([]);
  const [board, setBoard] = useState([]);
  const [category, setCategory] = useState('전체');
  const [search, setSearch] = useState('');
  const [selectedCard, setSelectedCard] = useState(null);
  const [showCardForm, setShowCardForm] = useState(false);
  const [cardSubmissions, setCardSubmissions] = useState([]);
  const [cardFormBusy, setCardFormBusy] = useState(false);
  const [adminSubmissions, setAdminSubmissions] = useState([]);
  const [reviewDrafts, setReviewDrafts] = useState({});
  const [reviewBusy, setReviewBusy] = useState('');
  const [tab, setTab] = useState('home');
  const [text, setText] = useState('');
  const [generationSource, setGenerationSource] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [stats, setStats] = useState(null);
  const [period, setPeriod] = useState('all');
  const [statsBusy, setStatsBusy] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const [requestId, setRequestId] = useState(() => crypto.randomUUID());
  const [linkedUsers, setLinkedUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [noteDrafts, setNoteDrafts] = useState({});
  const [noteBusy, setNoteBusy] = useState('');

  const dashboardPath = (value = period, target = selectedUser) => {
    const params = new URLSearchParams();
    if (value !== 'all') params.set('days', value);
    if (target?.id) params.set('user_id', target.id);
    const query = params.toString();
    return `/dashboard${query ? `?${query}` : ''}`;
  };

  async function load(account = user) {
    setError('');
    try {
      if (account?.role === 'admin') {
        const submissions = await request('/admin/card-submissions');
        setAdminSubmissions(await hydrateImages(submissions));
        setTab('admin'); setLoaded(true);
        return;
      }
      if (account?.role === 'caregiver') {
        const people = await request('/care/linked-users');
        const target = people[0] || null;
        setLinkedUsers(people); setSelectedUser(target); setCards([]); setRecommended([]); setTab('dashboard');
        setStats(target ? await request(dashboardPath(period, target)) : null); setLoaded(true);
        return;
      }
      const [rawCards, rawRecommended, dashboard, submissions] = await Promise.all([request('/cards'), request('/recommendations'), request(dashboardPath()), request('/cards/submissions')]);
      const [all, rec] = await Promise.all([hydrateImages(rawCards), hydrateImages(rawRecommended)]);
      setCards(all); setRecommended(rec); setStats(dashboard); setCardSubmissions(submissions); setBoard(loadBoard(account?.id, all)); setLoaded(true);
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
        await load(account);
      } catch { setToken(null); }
      finally { setAuthReady(true); }
    }
    restoreLogin();
    return () => window.speechSynthesis?.cancel();
  }, []);

  async function handleLogin(event) {
    event.preventDefault();
    if (authMode === 'register' && password !== passwordConfirm) { setError('비밀번호가 일치하지 않습니다.'); return; }
    setBusy(true); setError('');
    try {
      const path = authMode === 'register' ? '/auth/register' : '/auth/login';
      const body = authMode === 'register' ? { username, password, name } : { username, password };
      const result = await request(path, { method: 'POST', body: JSON.stringify(body) });
      setToken(result.access_token); setUser(result.user);
      await load(result.user);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); setAuthReady(true); }
  }

  async function handleLogout() {
    setBusy(true);
    try { await request('/auth/logout', { method: 'POST' }); } catch { /* local logout still applies */ }
    clearBoard(user?.id);
    window.speechSynthesis?.cancel(); setToken(null); setUser(null); setLoaded(false);
    [...cards, ...recommended, ...adminSubmissions].forEach(item => { if (item.image_src) URL.revokeObjectURL(item.image_src); });
    setCards([]); setRecommended([]); setStats(null); setBoard([]); setCardSubmissions([]); setAdminSubmissions([]); setLinkedUsers([]); setSelectedUser(null); setText(''); setError(''); setTab('home'); setBusy(false);
  }

  function updateBoard(next) {
    window.speechSynthesis?.cancel(); setSpeaking(false);
    setBoard(next); saveBoard(user?.id, next); setText(''); setGenerationSource(''); setRequestId(crypto.randomUUID());
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
      setGenerationSource(result.generation_source || 'rule');
      try {
        const [rec, dashboard] = await Promise.all([request('/recommendations'), request(dashboardPath())]);
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
  async function changePeriod(value) {
    setPeriod(value); setStatsBusy(true); setError('');
    try { setStats(await request(dashboardPath(value))); }
    catch (e) { setError(e.message); }
    finally { setStatsBusy(false); }
  }
  async function changeLinkedUser(value) {
    const target = linkedUsers.find(person => person.id === value);
    if (!target) return;
    setSelectedUser(target); setStatsBusy(true); setError('');
    try { setStats(await request(dashboardPath(period, target))); }
    catch (e) { setError(e.message); }
    finally { setStatsBusy(false); }
  }
  async function saveCaregiverNote(sessionId) {
    const content = (noteDrafts[sessionId] ?? stats.recent.find(row => row.id === sessionId)?.caregiver_note ?? '').trim();
    if (!content) { setError('메모 내용을 입력해 주세요.'); return; }
    setNoteBusy(sessionId); setError('');
    try {
      const saved = await request(`/care/notes/${sessionId}`, { method: 'PUT', body: JSON.stringify({ user_id: selectedUser.id, content }) });
      setStats(current => ({ ...current, recent: current.recent.map(row => row.id === sessionId ? { ...row, caregiver_note: saved.content } : row) }));
      setNoteDrafts(current => ({ ...current, [sessionId]: saved.content }));
    } catch (e) { setError(e.message); }
    finally { setNoteBusy(''); }
  }
  async function removeCaregiverNote(sessionId) {
    setNoteBusy(sessionId); setError('');
    try {
      await request(`/care/notes/${sessionId}?user_id=${encodeURIComponent(selectedUser.id)}`, { method: 'DELETE' });
      setStats(current => ({ ...current, recent: current.recent.map(row => row.id === sessionId ? { ...row, caregiver_note: null } : row) }));
      setNoteDrafts(current => ({ ...current, [sessionId]: '' }));
    } catch (e) { setError(e.message); }
    finally { setNoteBusy(''); }
  }
  async function submitCard(event) {
    event.preventDefault();
    const form = event.currentTarget;
    setCardFormBusy(true); setError('');
    try {
      const saved = await request('/cards/submissions', { method: 'POST', body: new FormData(form) });
      setCardSubmissions(current => [saved, ...current]);
      setShowCardForm(false);
      form.reset();
    } catch (e) { setError(e.message); }
    finally { setCardFormBusy(false); }
  }
  async function hydrateImages(items) {
    return Promise.all(items.map(async item => {
      if (!item.image_url) return item;
      try { return { ...item, image_src: URL.createObjectURL(await requestBlob(item.image_url)) }; }
      catch { return item; }
    }));
  }
  async function reviewCard(item, decision) {
    const reason = (reviewDrafts[item.id] || '').trim();
    if (decision === 'rejected' && !reason) { setError('반려 사유를 입력해 주세요.'); return; }
    setReviewBusy(item.id); setError('');
    try {
      const saved = await request(`/admin/card-submissions/${item.id}`, {
        method: 'PATCH', body: JSON.stringify({ decision, reason }),
      });
      setAdminSubmissions(current => current.map(row => row.id === item.id ? { ...row, ...saved } : row));
    } catch (e) { setError(e.message); }
    finally { setReviewBusy(''); }
  }
  function artStyle(card) {
    if (card.image_src) return { backgroundImage: `url(${card.image_src})`, backgroundPosition: 'center', backgroundSize: 'cover' };
    return { backgroundImage: `url(${cardSprite})`, backgroundPosition: `${(card.image_index % 6) * 20}% ${Math.floor(card.image_index / 6) * 50}%` };
  }
  function cardPicture(card, className = 'mini-card') {
    return <span key={card.id} className={className} title={card.label} aria-label={card.label} role="img" style={artStyle(card)} />;
  }
  function tile(card) {
    return <button className="card" key={card.id} disabled={busy} onClick={() => add(card)}>
      <span className="card-art" role="img" aria-label={`${card.label} 그림`} style={artStyle(card)} />
      <strong>{card.label}</strong>{card.reason && <small>{card.reason}</small>}
    </button>;
  }
  const visibleCards = cards.filter(card =>
    (category === '전체' || card.category === category)
    && card.label.includes(search.trim())
  );
  const todayLabel = new Intl.DateTimeFormat('ko-KR', {
    month: '2-digit', day: '2-digit', weekday: 'long',
  }).format(new Date());
  const pageTitle = user?.role === 'admin'
    ? '카드 등록 요청을 검토해요.'
    : user?.role === 'caregiver'
    ? `${selectedUser?.name || '보호 대상'}의 기록을 살펴봐요.`
    : tab === 'home'
      ? '오늘은 무엇을 해볼까요?'
      : tab === 'cards'
      ? `오늘의 추천 카드 ${recommended.length}개를 준비했어요.`
      : tab === 'catalog'
      ? `그림 카드 ${cards.length}개를 살펴보세요.`
      : '나의 의사소통 기록을 확인해요.';
  if (!authReady) return <main className="login-page"><p role="status">로그인 정보를 확인하는 중입니다…</p></main>;
  if (!user) return <main className="login-page"><section className="login-card">
    <div className="login-mascot" aria-hidden="true">💬</div><p className="eyebrow">그림으로 전하는 나의 이야기</p><h1>PESC MATE</h1>
    <h2>{authMode === 'login' ? '로그인' : '사용자 가입'}</h2><p className="muted">{authMode === 'login' ? '내 카드 기록과 추천을 불러옵니다.' : 'PECS 사용자 계정을 만들고 바로 시작합니다.'}</p>
    {error && <div role="alert" className="error">{error}</div>}
    <form onSubmit={handleLogin}>
      {authMode === 'register' && <label>이름<input autoFocus autoComplete="name" value={name} onChange={e => setName(e.target.value)} required minLength="1" maxLength="30" /></label>}
      <label>아이디<input autoFocus={authMode === 'login'} autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} required minLength={authMode === 'register' ? 4 : 1} maxLength={authMode === 'register' ? 32 : 64} pattern={authMode === 'register' ? '[A-Za-z0-9_-]+' : undefined} /></label>
      <label>비밀번호<input type="password" autoComplete={authMode === 'register' ? 'new-password' : 'current-password'} value={password} onChange={e => setPassword(e.target.value)} required minLength={authMode === 'register' ? 8 : 1} maxLength="128" /></label>
      {authMode === 'register' && <label>비밀번호 확인<input type="password" autoComplete="new-password" value={passwordConfirm} onChange={e => setPasswordConfirm(e.target.value)} required minLength="8" maxLength="128" /></label>}
      <button className="primary full" disabled={busy}>{busy ? '처리 중…' : authMode === 'login' ? '로그인' : '가입하고 시작하기'}</button>
    </form>
    <button className="auth-switch" disabled={busy} onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError(''); setUsername(''); setPassword(''); setPasswordConfirm(''); setName(''); }}>{authMode === 'login' ? '처음 이용하시나요? 사용자 가입' : '이미 계정이 있나요? 로그인'}</button>
    {authMode === 'login' && <p className="demo-account">사용자: <code>demo</code> / <code>demo1234</code><br />보호자: <code>caregiver</code> / <code>caregiver1234</code><br />관리자: <code>admin</code> / <code>admin1234</code></p>}
  </section></main>;
  return <main className="app">
    <aside className="sidebar">
      <div className="sidebar-brand"><span className="brand-mark" aria-hidden="true">💬</span><strong>PESC<br />MATE</strong></div>
      <div className="profile"><span className="profile-avatar" aria-hidden="true">{user.role === 'admin' ? '🛡️' : '😊'}</span><div><strong>{user.name}</strong><small>{user.role === 'admin' ? '컨텐츠 관리자' : user.role === 'caregiver' ? '보호자 계정' : 'PECS 사용자'}</small></div></div>
      <nav aria-label="주 메뉴">{user.role === 'admin' ? <button className="active" onClick={() => setTab('admin')}><span aria-hidden="true">☑</span>카드 승인<i aria-label={`승인 대기 ${adminSubmissions.filter(item => item.status === 'pending').length}개`}>{adminSubmissions.filter(item => item.status === 'pending').length}</i></button> : <>{user.role !== 'caregiver' && <><button className={tab === 'home' ? 'active' : ''} onClick={() => setTab('home')}><span aria-hidden="true">⌂</span>홈</button><button className={tab === 'cards' ? 'active' : ''} onClick={() => setTab('cards')}><span aria-hidden="true">▦</span>그림으로 말하기<i aria-label={`추천 카드 ${recommended.length}개`}>{recommended.length}</i></button><button className={tab === 'catalog' ? 'active' : ''} onClick={() => setTab('catalog')}><span aria-hidden="true">▤</span>카드</button></>}<button className={tab === 'dashboard' ? 'active' : ''} onClick={() => setTab('dashboard')}><span aria-hidden="true">▥</span>{user.role === 'caregiver' ? '보호자 현황' : '나의 이용 기록'}</button></>}</nav>
      <div className="sidebar-summary"><small>오늘의 의사소통</small><strong>{stats?.today_sessions || 0}개 문장</strong><span>{stats?.today_selections || 0}장의 카드를 사용했어요</span></div>
      <div className="sidebar-tip"><span aria-hidden="true">🌱</span><div><small>도움말</small><strong>그림을 차례대로 눌러<br />마음을 표현해 보세요.</strong></div></div>
      <button className="logout" onClick={handleLogout} disabled={busy}>로그아웃</button>
    </aside>
    <div className="app-content">
      <header className="topbar"><div><p className="eyebrow">오늘은 {todayLabel}</p><h1>{pageTitle}</h1></div><span className="status"><b className={loaded ? 'online' : ''}></b>{loaded ? '서비스 연결됨' : '연결 대기'}</span></header>
      {error && <div role="alert" className="error">{error} <button disabled={busy} onClick={() => load(user)}>다시 연결</button></div>}
      {!loaded && !error && <p role="status">카드를 불러오는 중입니다…</p>}
      {tab === 'home' && user.role !== 'caregiver' ? <section className="home-screen">
        <div className="home-heading"><div><p>원하는 활동을 선택해 주세요</p><h2>나의 PESC MATE</h2></div><span aria-hidden="true">🌈</span></div>
        <div className="home-launch-grid">
          <button className="home-launch-card communication" onClick={() => setTab('cards')}>
            <span className="home-card-visual" aria-hidden="true"><b>💬</b><i>🖼️</i></span>
            <span className="home-card-label"><small>카드를 골라 문장을 만들어요</small><strong>그림으로 말하기</strong><b aria-hidden="true">→</b></span>
          </button>
          <button className="home-launch-card records" onClick={() => setTab('dashboard')}>
            <span className="home-card-visual" aria-hidden="true"><b>📊</b><i>⭐</i></span>
            <span className="home-card-label"><small>내가 표현한 이야기를 봐요</small><strong>나의 이용 기록</strong><b aria-hidden="true">→</b></span>
          </button>
          <button className="home-launch-card catalog" onClick={() => setTab('catalog')}>
            <span className="home-card-visual" aria-hidden="true"><b>🖼️</b><i>🔎</i></span>
            <span className="home-card-label"><small>그림과 뜻을 차근차근 살펴봐요</small><strong>카드</strong><b aria-hidden="true">→</b></span>
          </button>
        </div>
        <div className="home-note"><span aria-hidden="true">🌱</span><div><strong>{user.name}님, 반가워요!</strong><p>그림 카드를 눌러 오늘의 이야기를 시작해 보세요.</p></div></div>
      </section> : tab === 'cards' && user.role !== 'caregiver' ? <div className="communication-layout">
      <section className="recommend-panel"><div className="stage-title"><span className="stage-back" aria-hidden="true">‹‹</span><div><strong>오늘의 추천 카드</strong><i aria-hidden="true"><b></b><b></b><b></b></i><p>자주 쓰는 카드를 골라 문장을 시작해요</p></div><span className="stage-helper" aria-hidden="true">🌱</span></div><div className="cards recommendations">{recommended.map(tile)}</div><div className="stage-ground" aria-hidden="true">▲　▲　　▲　　　▲　▲</div></section>
      <div className="workspace"><section><div className="section-title"><h2>무엇을 말하고 싶나요?</h2><input aria-label="카드 검색" placeholder="카드 이름 검색" value={search} onChange={e => setSearch(e.target.value)} /></div>
        <div className="categories" aria-label="카테고리">{['전체', ...new Set(cards.map(c => c.category))].map(c => <button key={c} aria-pressed={category === c} className={category === c ? 'active' : ''} onClick={() => setCategory(c)}>{c}</button>)}</div>
        <div className="cards">{visibleCards.map(tile)}</div>
        {loaded && !visibleCards.length && <p>검색 결과가 없어요.</p>}
      </section>
      <section className="board"><div className="section-title"><h2>나의 문장 <small>{board.length}/12</small></h2><button disabled={!board.length || busy} onClick={() => { if (window.confirm('선택한 카드를 모두 지울까요?')) updateBoard([]); }}>비우기</button></div>
        {!board.length && <p className="empty">왼쪽 카드를 눌러 보세요.<br />나 → 물 → 마시다</p>}
        <ol>{board.map((c, i) => <li key={`${c.id}-${i}`}><span>{c.symbol} {c.label}</span><div><button aria-label={`${i + 1}번째 카드 앞으로`} disabled={i === 0 || busy} onClick={() => move(i, -1)}>←</button><button aria-label={`${i + 1}번째 카드 뒤로`} disabled={i === board.length - 1 || busy} onClick={() => move(i, 1)}>→</button><button aria-label={`${i + 1}번째 카드 삭제`} disabled={busy} onClick={() => updateBoard(board.filter((_, n) => n !== i))}>×</button></div></li>)}</ol>
        <button className="primary full" disabled={!board.length || busy} onClick={generate}>{busy ? '문장을 만드는 중…' : '문장 만들기 · 저장'}</button>
        <div className="sentence" aria-live="polite">{text || '만든 문장이 여기에 표시돼요.'}{text && <small className={`source-badge ${generationSource}`}>{generationSource === 'ollama' ? 'Qwen · Ollama 생성' : '규칙 기반 생성'}</small>}</div>
        <div className="actions"><button className="primary" disabled={!text || busy || speaking} onClick={speak}>🔊 읽어주기</button><button disabled={!speaking} onClick={() => { window.speechSynthesis.cancel(); setSpeaking(false); }}>중지</button></div>
        <p className="muted">Ollama Qwen으로 문장을 만들며, 모델을 사용할 수 없으면 규칙 기반 문장으로 자동 전환합니다.</p>
      </section></div>
    </div> : tab === 'catalog' && user.role !== 'caregiver' ? <section className="card-catalog">
      <div className="catalog-toolbar">
        <div><h2>카드 보기</h2><p className="muted">카드를 눌러 그림과 뜻을 확인해 보세요.</p></div>
        <div className="catalog-actions"><input aria-label="카드 검색" placeholder="카드 이름 검색" value={search} onChange={event => setSearch(event.target.value)} /><button className="primary" onClick={() => setShowCardForm(true)}>+ 카드 등록</button></div>
      </div>
      <div className="categories" aria-label="카고리">{['전체', ...new Set(cards.map(card => card.category))].map(item => <button key={item} aria-pressed={category === item} className={category === item ? 'active' : ''} onClick={() => setCategory(item)}>{item}</button>)}</div>
      <div className="catalog-layout">
        <div className="catalog-grid" aria-label="카드 목록">{visibleCards.map(card => <button className="catalog-card" key={card.id} aria-pressed={selectedCard?.id === card.id} onClick={() => setSelectedCard(card)}>
          <span className="card-art" role="img" aria-label={`${card.label} 그림`} style={artStyle(card)} />
          <span><strong>{card.label}</strong><small>{card.category}</small></span>
        </button>)}</div>
        <aside className="card-detail" aria-live="polite">
          {selectedCard ? <><span className="detail-art" role="img" aria-label={`${selectedCard.label} 그림`} style={artStyle(selectedCard)} /><span className="detail-category">{selectedCard.category}</span><h3>{selectedCard.label}</h3><p>{selectedCard.label}을(를) 표현하는 PECS 카드예요.</p><button className="primary" onClick={() => { add(selectedCard); setTab('cards'); }}>문장에 사용하기</button></> : <div className="detail-empty"><span aria-hidden="true">👆</span><strong>카드를 선택해 주세요</strong><p>선택한 카드의 그림과 뜻이 여기에 보여요.</p></div>}
        </aside>
      </div>
      <div className="submission-list"><h3>나의 등록 요청</h3>{cardSubmissions.length ? <ul>{cardSubmissions.map(item => <li key={item.id}><span><strong>{item.label}</strong><small>{item.category} · {item.visibility === 'private' ? '나만 사용' : '공개 요청'}</small></span><b className={`submission-status ${item.status}`}>{item.status === 'pending' ? '승인 대기' : item.status}</b></li>)}</ul> : <p className="muted">아직 등록한 카드가 없어요.</p>}</div>
      {loaded && !visibleCards.length && <p className="empty">조건에 맞는 카드가 없어요. 다른 검색어나 카테고리를 선택해 보세요.</p>}
      {showCardForm && <div className="modal-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setShowCardForm(false); }}>
        <section className="card-form-modal" role="dialog" aria-modal="true" aria-labelledby="card-form-title">
          <div className="modal-heading"><div><h2 id="card-form-title">새 카드 등록</h2><p className="muted">등록할 카드의 정보를 입력해 주세요.</p></div><button type="button" aria-label="등록 폼 닫기" onClick={() => setShowCardForm(false)}>×</button></div>
          <form className="card-form" onSubmit={submitCard}>
            <label>카드명<input name="label" required maxLength="30" placeholder="예: 연필" /></label>
            <label>카드 뜻<textarea name="meaning" required maxLength="120" rows="3" placeholder="카드가 나타내는 뜻을 적어 주세요." /></label>
            <label>카테고리<select name="category" required defaultValue=""><option value="" disabled>카테고리 선택</option>{[...new Set(cards.map(card => card.category))].map(item => <option key={item}>{item}</option>)}</select></label>
            <label>공개 범위<select name="visibility" defaultValue="private"><option value="private">승인 후 나만 사용</option><option value="shared">승인 후 모든 사용자에게 공개 요청</option></select></label>
            <label>카드 이미지<input name="image" required type="file" accept="image/jpeg,image/png,image/webp" capture="environment" /></label>
            <p className="form-notice">제출한 카드는 관리자 승인 전까지 그림으로 말하기에 표시되지 않아요. JPG, PNG, WebP 파일을 5MB 이하, 가로·세로 128~4096px로 올려 주세요.</p>
            <div className="modal-actions"><button type="button" disabled={cardFormBusy} onClick={() => setShowCardForm(false)}>취소</button><button type="submit" className="primary" disabled={cardFormBusy}>{cardFormBusy ? '제출 중…' : '승인 요청'}</button></div>
          </form>
        </section>
      </div>}
    </section> : tab === 'admin' && user.role === 'admin' ? <section className="admin-review">
      <div className="panel-heading"><span aria-hidden="true">🛡️</span><div><h2>카드 승인 관리</h2><p className="muted">사용자가 제출한 카드를 확인하고 승인하거나 반려해 주세요.</p></div></div>
      <div className="review-summary"><strong>{adminSubmissions.filter(item => item.status === 'pending').length}</strong><span>승인 대기</span><strong>{adminSubmissions.filter(item => item.status === 'approved').length}</strong><span>승인 완료</span><strong>{adminSubmissions.filter(item => item.status === 'rejected').length}</strong><span>반려</span></div>
      <div className="review-grid">{adminSubmissions.map(item => <article className="review-card" key={item.id}>
        <span className="review-image" role="img" aria-label={`${item.label} 제출 이미지`} style={artStyle(item)} />
        <div className="review-content"><div className="review-title"><span><small>{item.category} · {item.visibility === 'private' ? '개인 카드' : '공개 카드'}</small><h3>{item.label}</h3></span><b className={`submission-status ${item.status}`}>{item.status === 'pending' ? '승인 대기' : item.status === 'approved' ? '승인' : '반려'}</b></div><p>{item.meaning}</p><small>제출자 {item.owner_id} · {new Date(item.created_at).toLocaleString('ko-KR')}</small>
          {item.status === 'pending' ? <><textarea aria-label={`${item.label} 검토 사유`} maxLength="500" placeholder="반려 시 사유를 입력해 주세요." value={reviewDrafts[item.id] || ''} onChange={event => setReviewDrafts(current => ({ ...current, [item.id]: event.target.value }))} /><div className="review-actions"><button className="primary" disabled={reviewBusy === item.id} onClick={() => reviewCard(item, 'approved')}>승인</button><button className="danger" disabled={reviewBusy === item.id} onClick={() => reviewCard(item, 'rejected')}>반려</button></div></> : item.review_reason && <p className="review-reason">처리 사유: {item.review_reason}</p>}
        </div>
      </article>)}</div>
      {!adminSubmissions.length && <p className="empty">아직 제출된 카드가 없습니다.</p>}
    </section> : <section className="dashboard"><div className="panel-heading"><span aria-hidden="true">🏆</span><div><h2>{user.role === 'caregiver' ? '보호 대상 의사소통 기록' : '나의 의사소통 기록'}</h2><p className="muted">{(selectedUser || user).name} · {period === 'all' ? '전체 기간' : `최근 ${period}일`} · 문장 저장 기준</p></div></div>
      {user.role === 'caregiver' && <label className="user-picker">조회 사용자<select value={selectedUser?.id || ''} onChange={event => changeLinkedUser(event.target.value)} disabled={statsBusy}>{linkedUsers.map(person => <option key={person.id} value={person.id}>{person.name} ({person.username})</option>)}</select></label>}
      <div className="period-filter" aria-label="조회 기간">{[['7', '최근 7일'], ['30', '최근 30일'], ['all', '전체']].map(([value, label]) => <button key={value} className={period === value ? 'active' : ''} aria-pressed={period === value} disabled={statsBusy} onClick={() => changePeriod(value)}>{label}</button>)}</div>
      {statsBusy && <p className="muted" role="status">통계를 불러오는 중입니다…</p>}
      {user.role === 'caregiver' && loaded && !selectedUser && <p className="empty">연결된 사용자가 없습니다.</p>}
      {stats && <div className={statsBusy ? 'stats-content loading' : 'stats-content'}>
        {user.role === 'caregiver' && <><div className="guardian-summary">
          <div><span>오늘 문장</span><strong>{stats.today_sessions}개</strong></div><div><span>오늘 사용 카드</span><strong>{stats.today_selections}장</strong></div>
          <div><span>주요 감정</span><strong>{stats.primary_emotion?.label || '기록 없음'}</strong></div><div><span>마지막 표현</span><strong>{stats.last_activity ? new Date(stats.last_activity).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) : '기록 없음'}</strong></div>
        </div><div className="guardian-grid"><article className="activity-panel"><h3>최근 7일 의사소통</h3><div className="activity-chart">{stats.daily_activity.map(day => { const max = Math.max(...stats.daily_activity.map(item => item.sessions), 1); return <div key={day.date}><span className="activity-value">{day.sessions}</span><i style={{ height: `${Math.max((day.sessions / max) * 100, 4)}%` }}></i><time>{new Date(`${day.date}T00:00:00`).toLocaleDateString('ko-KR', { weekday: 'short' })}</time></div>; })}</div></article>
          <article className="attention-panel"><h3>확인이 필요한 표현</h3>{stats.attention.length ? stats.attention.map(item => <div className="attention-item" key={item.id}>{cardPicture(item)}<span><strong>{item.label} · {item.count}회</strong><small>최근 {new Date(item.last_used_at).toLocaleString('ko-KR')}</small></span></div>) : <p className="muted">선택한 기간에 확인이 필요한 표현이 없어요.</p>}</article>
        </div></>}
        <div className="metrics"><div>저장한 문장<strong>{stats.sessions}개</strong></div><div>사용한 카드<strong>{stats.selections}장</strong></div></div>
        <h3>카테고리별 사용</h3>{Object.entries(stats.categories).map(([name, count]) => <div className="bar" key={name}><span>{name}</span><meter min="0" max={Math.max(stats.selections, 1)} value={count} /> {count}회</div>)}
        <h3>자주 사용한 카드</h3><div className="categories">{stats.top_cards.slice(0, 8).map(c => <span className="status" key={c.id}>{c.symbol} {c.label} · {c.count}회</span>)}</div>
        <h3>{user.role === 'caregiver' ? '최근 의사소통 타임라인' : '최근 문장'}</h3>{!stats.recent.length ? <p className="empty">선택한 기간에 기록이 없어요.</p> : <ul className="history">{stats.recent.map(r => <li key={r.id}>{user.role === 'caregiver' && <div className="history-cards">{r.cards.map((id, index) => cardPicture({ ...(CARD_META[id] || { id, label: id, image_index: 0 }), id: `${id}-${index}` }))}</div>}<span>{r.sentence}</span><time>{new Date(r.created_at).toLocaleString('ko-KR')}</time>{user.role === 'caregiver' && <div className="caregiver-note"><textarea aria-label={`${r.sentence} 보호자 메모`} maxLength="500" placeholder="상황이나 반응을 메모해 주세요" value={noteDrafts[r.id] ?? r.caregiver_note ?? ''} onChange={event => setNoteDrafts(current => ({ ...current, [r.id]: event.target.value }))} /><div><small>{(noteDrafts[r.id] ?? r.caregiver_note ?? '').length}/500</small><button disabled={noteBusy === r.id} onClick={() => saveCaregiverNote(r.id)}>메모 저장</button>{r.caregiver_note && <button disabled={noteBusy === r.id} onClick={() => removeCaregiverNote(r.id)}>삭제</button>}</div></div>}</li>)}</ul>}</div>}
      </section>}
      <footer>실행용 프로토타입 · 실제 개인정보를 입력하지 마세요.</footer>
    </div>
  </main>;
}

export default App;
