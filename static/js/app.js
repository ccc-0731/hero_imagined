document.addEventListener('DOMContentLoaded', () => {
  const heroForm = document.getElementById('hero-form');
  if (heroForm) {
    heroForm.addEventListener('submit', () => {
      const p = document.getElementById('progress');
      const bar = document.getElementById('bar');
      p.style.display = 'block';
      let v = 0;
      const t = setInterval(()=>{ v = Math.min(95, v+5); bar.style.width = v+'%'; }, 250);
      // allow the actual submit navigate to server; progress will stop when page reloads
    });
  }

  // Character generation
  const genCharacter = document.getElementById('gen-character');
  const genWorld = document.getElementById('gen-world');
  const craftStory = document.getElementById('craft-story');
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
      Array.from(form.elements).forEach(f=>{ if(f.name) data[f.name]=f.value });
      const resp = await fetch('/api/character',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answers:data})});
      const j = await resp.json();
      characterText = j.character;
      document.getElementById('character-output').textContent = characterText;
      if (characterText && worldText) craftStory.disabled = false;
    });
  }

  if (genWorld) {
    genWorld.addEventListener('click', async ()=>{
      showProgressFake(document.getElementById('world-output'));
      const form = document.getElementById('world-form');
      const data = {};
      Array.from(form.elements).forEach(f=>{ if(f.name) data[f.name]=f.value });
      // include detected topic if present on page
      const detected = document.querySelector('h2').textContent || '';
      const resp = await fetch('/api/world',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answers:data, detected:{topic:detected}})});
      const j = await resp.json();
      worldText = j.world;
      document.getElementById('world-output').textContent = worldText;
      if (characterText && worldText) craftStory.disabled = false;
    });
  }

  if (craftStory) {
    craftStory.addEventListener('click', async ()=>{
      craftStory.disabled = true;
      document.getElementById('final-section').style.display = 'block';
      document.getElementById('story-text').textContent = 'Crafting story...';
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
