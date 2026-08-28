document.addEventListener('DOMContentLoaded', function() {
  const defaultBtn = document.getElementById('sidebarDefaultBtn');
  const chatsBtn = document.getElementById('sidebarChatsBtn');
  const defaultPane = document.querySelector('.am-sidebar-default');
  const chatsPane = document.querySelector('.am-sidebar-chats');
  const chatHistoryList = document.getElementById('chatHistoryList');
  const newChatBtn = document.getElementById('newChatBtn');
  const chatThread = document.getElementById('chatThread');
  const composerForm = document.getElementById('composerForm');
  const composerInput = document.getElementById('composerInput');

  // Mocked history injected by template
  const initialHistory = window.__CHAT_HISTORY || [];
  let history = Array.isArray(initialHistory) ? initialHistory.slice() : [];
  let currentChat = { id: 'local-new', title: 'New chat', messages: [] };

  function setActiveTab(tab) {
    if (tab === 'chats') {
      defaultPane.style.display = 'none';
      chatsPane.style.display = '';
      defaultBtn.classList.remove('active');
      chatsBtn.classList.add('active');
    } else {
      defaultPane.style.display = '';
      chatsPane.style.display = 'none';
      defaultBtn.classList.add('active');
      chatsBtn.classList.remove('active');
    }
  }

  function renderHistory() {
    if (!chatHistoryList) return;
    chatHistoryList.innerHTML = '';
    history.forEach((c) => {
      const li = document.createElement('li');
      li.className = 'am-chat-history-item';
      li.dataset.chatId = c.id;
      li.style.padding = '8px';
      li.style.borderBottom = '1px solid #eee';
      li.style.cursor = 'pointer';

      const title = document.createElement('div');
      title.className = 'am-chat-history-title';
      title.innerHTML = `<strong>${c.title}</strong>`;

      const preview = document.createElement('div');
      preview.className = 'am-chat-history-preview text-muted';
      preview.style.fontSize = '0.9em';
      preview.textContent = c.preview || (c.messages && c.messages.length ? c.messages[c.messages.length-1].text.substring(0, 80) : 'No messages');

      li.appendChild(title);
      li.appendChild(preview);

      li.addEventListener('click', () => {
        loadChatById(c.id);
        setActiveTab('default');
      });

      chatHistoryList.appendChild(li);
    });
  }

  function loadChatById(id) {
    const found = history.find(h => String(h.id) === String(id));
    if (found) {
      currentChat = JSON.parse(JSON.stringify(found)); // copy to avoid mutating original history entry
      renderThread();
    }
  }

  function renderThread() {
    if (!chatThread) return;
    chatThread.innerHTML = '';
    (currentChat.messages || []).forEach((msg) => {
      const wrapper = document.createElement('div');
      const p = document.createElement('p');
      p.textContent = msg.text;

      if (msg.role === 'student') {
        wrapper.className = 'am-bubble am-bubble-student';
        const label = document.createElement('div');
        label.className = 'am-bubble-label';
        label.innerHTML = '<i class="ti ti-user"></i> You';
        wrapper.appendChild(label);
        wrapper.appendChild(p);
      } else {
        wrapper.className = 'am-bubble am-bubble-agent';
        const label = document.createElement('div');
        label.className = 'am-bubble-label';
        label.innerHTML = '<i class="ti ti-brain"></i> Coding Agent';
        wrapper.appendChild(label);
        if (msg.flag) {
          const flag = document.createElement('div');
          flag.className = 'am-flag-tag';
          flag.innerHTML = '<i class="ti ti-alert-triangle"></i> ' + msg.flag;
          wrapper.appendChild(flag);
        }
        if (msg.concept) {
          const concept = document.createElement('div');
          concept.className = 'am-concept-tag';
          concept.innerHTML = '<i class="ti ti-bulb"></i> Concept check';
          wrapper.appendChild(concept);
        }
        wrapper.appendChild(p);
      }

      chatThread.appendChild(wrapper);
    });

    // scroll to bottom
    chatThread.scrollTop = chatThread.scrollHeight;
  }

  function startNewChat() {
    const newId = 'local-' + Date.now();
    currentChat = { id: newId, title: 'New chat', preview: '', messages: [] };
    // add to front of history for quick access
    history.unshift(Object.assign({}, currentChat));
    renderHistory();
    renderThread();
    setActiveTab('default');
  }

  if (newChatBtn) newChatBtn.addEventListener('click', (e) => {
    e.preventDefault();
    startNewChat();
  });

  if (defaultBtn) defaultBtn.addEventListener('click', () => setActiveTab('default'));
  if (chatsBtn) chatsBtn.addEventListener('click', () => setActiveTab('chats'));

  if (composerForm) {
    composerForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = (composerInput && composerInput.value || '').trim();
      if (!text) return;

      // append student message
      currentChat.messages = currentChat.messages || [];
      currentChat.messages.push({ role: 'student', text: text });
      composerInput.value = '';
      renderThread();

      // update preview in history (if exists)
      const histEntry = history.find(h => String(h.id) === String(currentChat.id));
      if (histEntry) {
        histEntry.preview = text.substring(0, 120);
        histEntry.messages = currentChat.messages.slice();
        renderHistory();
      }

      // simulate a mocked agent reply
      setTimeout(() => {
        const reply = { role: 'agent', text: '(mock) Agent response to: ' + text };
        currentChat.messages.push(reply);
        if (histEntry) {
          histEntry.messages = currentChat.messages.slice();
          histEntry.preview = reply.text.substring(0, 120);
        }
        renderThread();
        renderHistory();
      }, 700);
    });
  }

  // initialize
  renderHistory();
  // if there is at least one history item, load the first one into the thread
  if (history.length > 0) {
    loadChatById(history[0].id);
  } else {
    renderThread();
  }

  // default view
  setActiveTab('default');
});
