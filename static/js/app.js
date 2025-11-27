document.addEventListener('DOMContentLoaded', () => {
  const heroForm = document.getElementById('hero-form');
  if (heroForm) {
    heroForm.addEventListener('submit', () => {
      const p = document.getElementById('progress');
      const bar = document.getElementById('bar');
      p.style.display = 'block';
      let v = 0;
      const t = setInterval(()=>{ v = Math.min(95, v+5); bar.style.width = v+'%'; }, 250);
    });
  }

  // Fetch and populate dynamic questions on builder page
  const charQuestionsDiv = document.getElementById('character-questions');
  const worldQuestionsDiv = document.getElementById('world-questions');
  
  if (charQuestionsDiv && worldQuestionsDiv) {
    const detectedTopic = document.getElementById('detected-topic')?.textContent?.trim() || 'fantasy';
    const rawPrompt = document.querySelector('[data-raw-prompt]')?.getAttribute('data-raw-prompt') || '';
    
    fetch('/api/generate-questions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_prompt: rawPrompt,
        detected_topic: detectedTopic
      })
    })
    .then(r => r.json())
    .then(data => {
      // Populate character questions
      const charQs = data.character_questions || [];
      charQuestionsDiv.innerHTML = charQs.map(q => `
        <label>${q.question}</label>
        <textarea name="char_q${q.number}" placeholder="${q.example}"></textarea>
      `).join('');
      
      // Populate world questions
      const worldQs = data.world_questions || [];
      worldQuestionsDiv.innerHTML = worldQs.map(q => `
        <label>${q.question}</label>
        <textarea name="world_q${q.number}" placeholder="${q.example}"></textarea>
      `).join('');
    })
    .catch(err => {
      console.error('Error fetching questions:', err);
      charQuestionsDiv.innerHTML = '<p>Error loading questions. Please refresh.</p>';
    });
  }

  // Character and World generation
  const genCharacter = document.getElementById('gen-character');
  const genWorld = document.getElementById('gen-world');
  const doneButton = document.getElementById('done-button');
  let characterText = '';
  let worldText = '';

  function showProgressFake(el){
    el.textContent = 'Generating...';
  }

  if (genCharacter) {
    genCharacter.addEventListener('click', async ()=>{
      showProgressFake(document.getElementById('character-output'));
      const form = document.getElementById('character-form');
      const data = {};
      Array.from(form.elements).forEach(f=>{ if(f.name && f.value) data[f.name]=f.value });
      const resp = await fetch('/api/character',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answers:data})});
      const j = await resp.json();
      characterText = j.character;
      document.getElementById('character-output').textContent = characterText;
      checkDoneButtonState();
    });
  }

  if (genWorld) {
    genWorld.addEventListener('click', async ()=>{
      showProgressFake(document.getElementById('world-output'));
      const form = document.getElementById('world-form');
      const data = {};
      Array.from(form.elements).forEach(f=>{ if(f.name && f.value) data[f.name]=f.value });
      const detected = document.getElementById('detected-topic')?.textContent || '';
      const resp = await fetch('/api/world',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answers:data, detected:{topic:detected}})});
      const j = await resp.json();
      worldText = j.world;
      document.getElementById('world-output').textContent = worldText;
      checkDoneButtonState();
    });
  }

  function checkDoneButtonState() {
    if (characterText && worldText) {
      doneButton.disabled = false;
    }
  }

  if (doneButton) {
    doneButton.addEventListener('click', async ()=>{
      doneButton.disabled = true;
      document.getElementById('final-section').style.display = 'block';
      document.getElementById('story-text').textContent = 'Crafting your story...';
      const resp = await fetch('/generate_story',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({character:characterText, world:worldText})});
      const j = await resp.json();
      if (j.error){ document.getElementById('story-text').textContent = 'Error: '+JSON.stringify(j); return }
      document.getElementById('story-text').textContent = j.story;
      // images
      const imagesDiv = document.getElementById('images'); imagesDiv.innerHTML='';
      (j.images||[]).forEach(src=>{ const img=document.createElement('img'); img.src=src; img.className='illustration'; imagesDiv.appendChild(img); });
      // audio
      const audioDiv = document.getElementById('audio-player'); audioDiv.innerHTML='';
      if (j.audio){ const a = document.createElement('audio'); a.controls=true; a.src=j.audio; audioDiv.appendChild(a); }
      document.getElementById('analogy').textContent = j.analogy || '';
    });
  }

});

