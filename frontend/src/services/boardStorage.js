const BOARD_KEY_PREFIX = 'pesc-mate-board:';
const MAX_BOARD_SIZE = 12;

function keyFor(userId) {
  return `${BOARD_KEY_PREFIX}${userId}`;
}

export function loadBoard(userId, cards) {
  if (!userId) return [];

  try {
    const savedIds = JSON.parse(localStorage.getItem(keyFor(userId)) || '[]');
    if (!Array.isArray(savedIds)) return [];

    const cardsById = new Map(cards.map(card => [card.id, card]));
    const restored = savedIds
      .slice(0, MAX_BOARD_SIZE)
      .map(id => cardsById.get(id))
      .filter(Boolean);

    // Remove stale or malformed entries while preserving valid duplicates and order.
    saveBoard(userId, restored);
    return restored;
  } catch {
    clearBoard(userId);
    return [];
  }
}

export function saveBoard(userId, board) {
  if (!userId) return;

  try {
    if (board.length) localStorage.setItem(keyFor(userId), JSON.stringify(board.map(card => card.id)));
    else clearBoard(userId);
  } catch {
    // Card selection must continue even when browser storage is unavailable.
  }
}

export function clearBoard(userId) {
  if (!userId) return;

  try {
    localStorage.removeItem(keyFor(userId));
  } catch {
    // Logging out and clearing the visible board must still succeed.
  }
}
