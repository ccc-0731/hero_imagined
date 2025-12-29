document.addEventListener('DOMContentLoaded', () => {
  const heroForm = document.getElementById('hero-form');
  if (heroForm) {
    heroForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const p = document.getElementById('progress');
      const bar = document.getElementById('bar');
      p.style.display = 'block';
      let v = 0;
      const t = setInterval(()=>{ v = Math.min(95, v+5); bar.style.width = v+'%'; }, 250);
      
      // Submit form normally so it redirects to /builder
      heroForm.submit();
    });
  }

  // Fetch and populate dynamic questions on builder page
  const charQuestionsDiv = document.getElementById('character-questions');
  const worldQuestionsDiv = document.getElementById('world-questions');
  
  if (charQuestionsDiv && worldQuestionsDiv) {
    const detectedTopic = document.getElementById('detected-topic')?.textContent?.trim() || 'fantasy';
    const rawPrompt = document.querySelector('[data-raw-prompt]')?.getAttribute('data-raw-prompt') || '';
    
    // Show loading message
    charQuestionsDiv.innerHTML = '<p>Loading character building questions...</p>';
    worldQuestionsDiv.innerHTML = '<p>Loading world building questions...</p>';
    
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
      if (charQs.length > 0) {
        charQuestionsDiv.innerHTML = charQs.map(q => `
          <label>${q.question}</label>
          <textarea name="char_q${q.number}" placeholder="${q.example}"></textarea>
        `).join('');
      } else {
        charQuestionsDiv.innerHTML = '<p>No character questions loaded. Please refresh.</p>';
      }
      
      // Populate world questions
      const worldQs = data.world_questions || [];
      if (worldQs.length > 0) {
        worldQuestionsDiv.innerHTML = worldQs.map(q => `
          <label>${q.question}</label>
          <textarea name="world_q${q.number}" placeholder="${q.example}"></textarea>
        `).join('');
      } else {
        worldQuestionsDiv.innerHTML = '<p>No world questions loaded. Please refresh.</p>';
      }
      
      console.log(`Loaded ${charQs.length} character questions and ${worldQs.length} world questions`);
    })
    .catch(err => {
      console.error('Error fetching questions:', err);
      charQuestionsDiv.innerHTML = '<p>Error loading character questions. Please refresh.</p>';
      worldQuestionsDiv.innerHTML = '<p>Error loading world questions. Please refresh.</p>';
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
      if (!resp.ok) {
        alert(j.error || 'Please build the character before continuing!');
        document.getElementById('character-output').textContent = '';
        return;
      }
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
      if (!resp.ok) {
        alert(j.error || 'Please build the world before continuing!');
        document.getElementById('world-output').textContent = '';
        return;
      }
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
      
      // Show progress checklist
      const checklist = document.getElementById('progress-checklist');
      checklist.style.display = 'block';
      const checklistItems = document.getElementById('checklist-items');
      checklistItems.innerHTML = '';
      
      const resp = await fetch('/generate_story',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({character:characterText, world:worldText})});
      const j = await resp.json();

      if (j.error){ 
        document.getElementById('story-text').textContent = 'Error: '+JSON.stringify(j); 
        return;
      }

      // Keep a mutable storyData object to accumulate images/audio as they arrive
      const storyData = Object.assign({}, j);
      storyData.images = storyData.images || [];

      // Helper to render checklist
      let steps = j.steps || [];
      function renderChecklist(){
        checklistItems.innerHTML = steps.map(step => {
          const icon = step.status === 'complete' ? '✓' : (step.status === 'skipped' ? '⊘' : (step.status === 'in-progress' ? '◐' : '◌'));
          const color = step.status === 'complete' ? '#10b981' : (step.status === 'skipped' ? '#9ca3af' : (step.status === 'in-progress' ? '#f59e0b' : '#6b7280'));
          return `<div data-step="${step.name}" style="margin: 8px 0; display: flex; align-items: center; gap: 10px;">
            <span style="color: ${color}; font-weight: bold; font-size: 18px;">${icon}</span>
            <span style="color: #333;">${step.name}</span>
            <span style="color: #999; font-size: 12px;">${step.status}</span>
          </div>`;
        }).join('');
      }

      function updateStep(name, status){
        const s = steps.find(st => st.name === name);
        if (s) s.status = status;
        renderChecklist();
      }

      renderChecklist();

      // Display story (server returns sanitized HTML from Markdown)
      document.getElementById('story-text').innerHTML = j.story_html || '<p>Story generation failed.</p>';

      // Display analogy (real-life inspiration)
      document.getElementById('analogy').innerHTML = j.analogy_html || '<p>Analogy generation skipped.</p>';

      // Show PDF download button (will use updated storyData)
      const pdfBtn = document.getElementById('download-pdf-btn');
      pdfBtn.style.display = 'inline-block';
      pdfBtn.addEventListener('click', () => generateAndDownloadPDF(storyData));

      // Images container and audio container
      const imagesDiv = document.getElementById('images'); 
      imagesDiv.innerHTML='';
      const audioSection = document.getElementById('audio-section');
      const audioDiv = document.getElementById('audio-player');
      audioDiv.innerHTML='';

      // Sequentially request hero image, background image, then BGM — updating checklist each time
      // 1) Hero scene
      // First: extract hero name (if requested)
      if (steps.find(s=>s.name==='Hero Name Extraction')){
        updateStep('Hero Name Extraction','in-progress');
        try{
          const nresp = await fetch('/extract_hero_name',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({character: characterText})});
          const nj = await nresp.json();
          if (nresp.ok && nj.hero_name){
            storyData.hero_name = nj.hero_name;
            updateStep('Hero Name Extraction','complete');
          } else {
            storyData.hero_name = storyData.hero_name || 'the hero';
            updateStep('Hero Name Extraction','skipped');
          }
        }catch(err){
          console.error('Hero name extraction error', err);
          storyData.hero_name = storyData.hero_name || 'the hero';
          updateStep('Hero Name Extraction','skipped');
        }
      }

      // Now hero scene
      if (steps.find(s=>s.name==='Hero Scene Image')){
        updateStep('Hero Scene Image', 'in-progress');
        try{
          const hresp = await fetch('/generate_image', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({type:'hero', character: characterText, story_excerpt: (j.story || '').slice(0,300)})});
          const hj = await hresp.json();
          if (hj.image_url){
            const img = document.createElement('img'); img.src = hj.image_url; img.className='illustration';
            imagesDiv.insertBefore(img, imagesDiv.firstChild);
            storyData.images = storyData.images || []; storyData.images.unshift(hj.image_url);
            updateStep('Hero Scene Image', 'complete');
          } else {
            updateStep('Hero Scene Image', 'skipped');
          }
        }catch(err){
          console.error('Hero image error', err);
          updateStep('Hero Scene Image','skipped');
        }
      }

      // 2) Background image
      if (steps.find(s=>s.name==='Background Image')){
        updateStep('Background Image', 'in-progress');
        try{
          const bresp = await fetch('/generate_image', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({type:'background', world: worldText})});
          const bj = await bresp.json();
          if (bj.image_url){
            const img = document.createElement('img'); img.src = bj.image_url; img.className='illustration';
            imagesDiv.appendChild(img);
            storyData.images = storyData.images || []; storyData.images.push(bj.image_url);
            updateStep('Background Image', 'complete');
          } else {
            updateStep('Background Image','skipped');
          }
        }catch(err){
          console.error('Background image error', err);
          updateStep('Background Image','skipped');
        }
      }

      // 3) Background music
      if (steps.find(s=>s.name==='Background Music')){
        updateStep('Background Music', 'in-progress');
        try{
          const mresp = await fetch('/generate_bgm', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({world: worldText, character: characterText, hero_name: storyData.hero_name || j.hero_name})});
          const mj = await mresp.json();
          if (mj.audio_url){
            storyData.audio = mj.audio_url;
            audioSection.style.display = 'block';
            const a = document.createElement('audio'); a.controls=true; a.src=mj.audio_url; audioDiv.appendChild(a);
            updateStep('Background Music', 'complete');
          } else {
            updateStep('Background Music','skipped');
          }
        }catch(err){
          console.error('BGM error', err);
          updateStep('Background Music','skipped');
        }
      }

      // 4) Real-life analogy (deferred)
      if (steps.find(s=>s.name==='Real-life Inspiration')){
        updateStep('Real-life Inspiration','in-progress');
        try{
          const aresp = await fetch('/generate_analogy', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({hero_name: storyData.hero_name || j.hero_name, story: storyData.story})});
          const aj = await aresp.json();
          if (aj.analogy_html){
            storyData.analogy = aj.analogy_md || '';
            storyData.analogy_html = aj.analogy_html;
            document.getElementById('analogy').innerHTML = aj.analogy_html;
            updateStep('Real-life Inspiration','complete');
          } else {
            updateStep('Real-life Inspiration','skipped');
          }
        }catch(err){
          console.error('Analogy error', err);
          updateStep('Real-life Inspiration','skipped');
        }
      }
    });
  }
  
  // PDF Generation and Download
  async function generateAndDownloadPDF(storyData) {
    const btn = document.getElementById('download-pdf-btn');
    const originalText = btn.textContent;
    btn.textContent = '⏳ Generating PDF...';
    btn.disabled = true;
    
    try {
      const response = await fetch('/generate_pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          story: storyData.story,
          character: storyData.character,
          world: storyData.world,
          hero_name: storyData.hero_name,
          analogy: storyData.analogy,
          images: storyData.images,
          bg_image: storyData.images && storyData.images.length > 0 ? storyData.images[0] : null
        })
      });
      
      if (!response.ok) {
        throw new Error('PDF generation failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${storyData.hero_name.replace(/\s+/g, '_')}_Adventure.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Error generating PDF:', err);
      alert('Failed to generate PDF. Please try again.');
    } finally {
      btn.textContent = originalText;
      btn.disabled = false;
    }
  }

});

