import json, re, shutil, subprocess, textwrap, wave
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import requests, streamlit as st, pyttsx3
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'output'; FRAMES=OUT/'frames'; OUT.mkdir(exist_ok=True); FRAMES.mkdir(exist_ok=True)
SYSTEM='''You are an expert short-form video writer. Return ONLY valid JSON: {"title":"...","description":"...","hashtags":["#tag"],"scenes":[{"narration":"spoken words","caption":"max 8 words","visual":"brief visual direction"}]}. Create 5-8 scenes for a YouTube Short. Start with a strong hook. Use cautious factual language, do not invent statistics or citations, and end with a memorable takeaway. Write original wording.'''
st.set_page_config(page_title='Shorts Studio',page_icon='🎬',layout='wide')

def parse_json(s):
    s=re.sub(r'^\`\`\`(?:json)?\s*|\s*\`\`\`$','',s.strip(),flags=re.I)
    a,b=s.find('{'),s.rfind('}')
    if a<0 or b<a: raise ValueError('AI did not return JSON.')
    return json.loads(s[a:b+1])

def generate(prompt, provider, model, key):
    if provider=='Ollama (local/free)':
        r=requests.post('http://127.0.0.1:11434/api/chat',json={'model':model,'stream':False,'format':'json','messages':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}],'options':{'num_ctx':2048,'temperature':0.7}},timeout=240); r.raise_for_status(); return parse_json(r.json()['message']['content'])
    if provider=='OpenAI GPT':
        r=requests.post('https://api.openai.com/v1/responses',headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'},json={'model':model,'instructions':SYSTEM,'input':prompt},timeout=180); r.raise_for_status()
        body=r.json(); text=body.get('output_text','')
        if not text:
            text=''.join(part.get('text','') for item in body.get('output',[]) for part in item.get('content',[]) if part.get('type')=='output_text')
        return parse_json(text)
    r=requests.post('https://api.anthropic.com/v1/messages',headers={'x-api-key':key,'anthropic-version':'2023-06-01','content-type':'application/json'},json={'model':model,'max_tokens':3000,'system':SYSTEM,'messages':[{'role':'user','content':prompt}]},timeout=180); r.raise_for_status(); return parse_json(''.join(x.get('text','') for x in r.json()['content'] if x.get('type')=='text'))

def video_id(url):
    p=urlparse(url.strip())
    if p.hostname in ('youtu.be','www.youtu.be'): return p.path.strip('/').split('/')[0]
    if p.hostname and 'youtube.com' in p.hostname:
        if p.path=='/watch': return parse_qs(p.query).get('v',[None])[0]
        parts=p.path.strip('/').split('/')
        if len(parts)>1 and parts[0] in ('shorts','embed','live'): return parts[1]
    return None

def transcript(url):
    from youtube_transcript_api import YouTubeTranscriptApi
    vid=video_id(url)
    if not vid: raise ValueError('Invalid YouTube URL')
    data=YouTubeTranscriptApi().fetch(vid,languages=['en'])
    return ' '.join(x.text for x in data)

def web_search(query, limit=5):
    from ddgs import DDGS
    return list(DDGS().text(query, max_results=limit))

def normalize_script(data):
    cleaned=[]
    for scene in data.get('scenes',[]):
        narration=str(scene.get('narration','')).strip()
        if narration:
            cleaned.append({'narration':narration,'caption':str(scene.get('caption',narration[:45]))[:90],'visual':str(scene.get('visual','Clean cinematic background'))})
    if len(cleaned)<3: raise ValueError('AI returned fewer than 3 usable scenes. Try again.')
    return {'title':str(data.get('title','My YouTube Short'))[:100],'description':str(data.get('description','')),'hashtags':data.get('hashtags',[]),'scenes':cleaned[:8]}

def font(size,bold=False):
    p=Path(r'C:\Windows\Fonts\arialbd.ttf' if bold else r'C:\Windows\Fonts\arial.ttf')
    return ImageFont.truetype(str(p),size) if p.exists() else ImageFont.load_default()

def scene_card(i,n,caption,visual,path):
    w,h=1080,1920; im=Image.new('RGB',(w,h),(12,20,39)); d=ImageDraw.Draw(im,'RGBA')
    for y in range(h):
        t=y/h; d.line((0,y,w,y),fill=(int(12+13*t),int(20+18*t),int(39+27*t)))
    d.ellipse((720,130,1280,690),fill=(35,100,155,65)); d.ellipse((-250,1200,430,1850),fill=(115,55,135,50))
    d.rounded_rectangle((65,90,1015,1830),radius=45,outline=(255,255,255,55),width=3)
    d.text((115,155),'SHORTS STUDIO',font=font(38,True),fill=(120,210,255)); d.text((115,235),f'SCENE {i:02d} / {n:02d}',font=font(40),fill=(210,220,235))
    lines=textwrap.wrap(caption,width=17) or [caption]; y=(h-len(lines)*105)//2
    for line in lines:
        box=d.textbbox((0,0),line,font=font(82,True)); d.text(((w-(box[2]-box[0]))//2,y),line,font=font(82,True),fill='white',stroke_width=2,stroke_fill=(0,0,0,100)); y+=105
    d.text((115,1600),textwrap.fill(visual[:100],width=36),font=font(36),fill=(185,200,220)); d.text((115,1750),'Vertical video • 9:16',font=font(34,True),fill=(120,210,255)); im.save(path)

def make_voice(text,path,gender):
    e=pyttsx3.init(); e.setProperty('rate',168); e.setProperty('volume',1.0)
    if gender!='Default':
        for v in e.getProperty('voices'):
            if gender.lower() in (v.name+' '+v.id).lower(): e.setProperty('voice',v.id); break
    e.save_to_file(text,str(path)); e.runAndWait(); e.stop()
    if not path.exists() or path.stat().st_size<1000: raise RuntimeError('Windows offline speech engine did not create audio. Check installed Windows voices.')

def duration_wav(p):
    with wave.open(str(p),'rb') as w: return w.getnframes()/w.getframerate()

def render(data,audio,music=None):
    ff=shutil.which('ffmpeg')
    if not ff: raise RuntimeError('FFmpeg not found on PATH. Install it and reopen PowerShell.')
    for p in FRAMES.glob('*.png'): p.unlink()
    scenes=data['scenes']; paths=[]
    for i,s in enumerate(scenes,1):
        p=FRAMES/f'scene_{i:02d}.png'; scene_card(i,len(scenes),s['caption'],s['visual'],p); paths.append(p)
    total=duration_wav(audio); weights=[max(1,len(s['narration'].split())) for s in scenes]; denom=sum(weights)
    concat=OUT/'scenes.txt'
    with concat.open('w',encoding='utf-8') as f:
        for p,w in zip(paths,weights): f.write(f"file '{p.resolve().as_posix()}'\nduration {total*w/denom:.3f}\n")
        f.write(f"file '{paths[-1].resolve().as_posix()}'\n")
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S'); dest=OUT/f'short_{stamp}.mp4'
    cmd=[ff,'-y','-f','concat','-safe','0','-i',str(concat),'-i',str(audio)]
    if music:
        cmd += ['-stream_loop','-1','-i',str(music),'-filter_complex','[2:a]volume=0.10[bg];[1:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]','-map','0:v','-map','[aout]']
    else: cmd += ['-map','0:v','-map','1:a']
    cmd += ['-vf','scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,format=yuv420p','-r','30','-c:v','libx264','-preset','ultrafast','-crf','24','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',str(dest)]
    res=subprocess.run(cmd,capture_output=True,text=True,timeout=900)
    if res.returncode: raise RuntimeError(res.stderr[-3000:])
    return dest,paths[0]

st.title('🎬 Shorts Studio'); st.caption('Local-first YouTube Shorts creator for Windows • Ollama / GPT / Claude')
with st.sidebar:
    st.header('AI provider')
    provider=st.selectbox('Script-writing engine',['Ollama (local/free)','OpenAI GPT','Anthropic Claude','Compare GPT + Claude'])
    ollama_model=st.text_input('Ollama model','qwen3:1.7b')
    openai_model=st.text_input('OpenAI model','gpt-6-luna')
    claude_model=st.text_input('Claude model','claude-haiku-5-5')
    openai_key=st.text_input('OpenAI API key (not saved)',type='password')
    claude_key=st.text_input('Anthropic API key (not saved)',type='password')
    st.caption('Cloud API calls require internet and may cost money. Compare mode sends a request to both providers. Keys are not written to disk.')
st.header('1. Video brief')
topic=st.text_input('Topic',placeholder='5 surprising facts about the human brain')
a,b,c=st.columns(3)
with a: length=st.selectbox('Duration',['30 seconds','45 seconds','60 seconds'])
with b: style=st.selectbox('Style',['Cinematic documentary','Mysterious storytelling','Educational and clear','Fast-paced facts','Motivational'])
with c: audience=st.selectbox('Audience',['General audience','Students','Technology enthusiasts','Science enthusiasts','History enthusiasts'])
st.header('2. Research (optional)')
urls=st.text_area('YouTube URLs, one per line',height=75)
notes=st.text_area('Notes and source excerpts',height=90)
search_online=st.checkbox('Also search the web for background sources (requires internet)',value=False)
if st.button('Gather research'):
    bits=[]
    for u in urls.splitlines():
        if u.strip():
            try:
                with st.spinner('Fetching available transcript...'): bits.append(f'SOURCE {u}\n{transcript(u.strip())[:6500]}')
                st.success('Transcript retrieved')
            except Exception as ex: st.warning(f'Transcript unavailable: {ex}')
    if search_online and topic.strip():
        try:
            with st.spinner('Searching the web...'):
                results=web_search(topic,5)
            for item in results:
                bits.append(f"WEB RESULT: {item.get('title','')}\nURL: {item.get('href','')}\n{item.get('body','')}")
            st.success(f'Added {len(results)} web results.')
        except Exception as ex: st.warning(f'Web search unavailable: {ex}')
    st.session_state['research']='\n\n'.join(bits)
if st.session_state.get('research'): st.text_area('Retrieved research excerpts',st.session_state['research'],height=170)
st.header('3. Generate script')
if st.button('Generate script',type='primary',disabled=not topic.strip(),use_container_width=True):
    prompt=f'Topic: {topic}\nDuration: {length}\nStyle: {style}\nAudience: {audience}\nResearch: {st.session_state.get("research","")}\nUser notes: {notes}\nUse supplied material responsibly. Do not invent sources or facts.'
    try:
        with st.spinner('Generating script...'):
            if provider=='Ollama (local/free)':
                data=generate(prompt,provider,ollama_model,'')
            elif provider=='OpenAI GPT':
                if not openai_key: raise ValueError('Enter your OpenAI API key in the sidebar.')
                data=generate(prompt,provider,openai_model,openai_key)
            elif provider=='Anthropic Claude':
                if not claude_key: raise ValueError('Enter your Anthropic API key in the sidebar.')
                data=generate(prompt,provider,claude_model,claude_key)
            else:
                if not openai_key or not claude_key: raise ValueError('Enter both API keys to compare GPT and Claude.')
                gpt_data=generate(prompt,'OpenAI GPT',openai_model,openai_key)
                claude_data=generate(prompt,'Anthropic Claude',claude_model,claude_key)
                st.session_state['gpt_draft']=normalize_script(gpt_data)
                st.session_state['claude_draft']=normalize_script(claude_data)
                data=st.session_state['gpt_draft']
        data=normalize_script(data)
        st.session_state['draft']=data; st.success('Draft generated. Edit it before rendering.')
    except Exception as ex: st.error(f'Generation failed: {ex}')
if 'gpt_draft' in st.session_state and 'claude_draft' in st.session_state:
    which=st.radio('Choose the draft to review',['GPT draft','Claude draft'],horizontal=True)
    st.session_state['draft']=st.session_state['gpt_draft'] if which=='GPT draft' else st.session_state['claude_draft']
if 'draft' in st.session_state:
    data=st.session_state['draft']; st.header('4. Review and edit')
    title=st.text_input('Title',data.get('title',''))
    desc=st.text_area('Description',data.get('description',''))
    tags=st.text_input('Hashtags',' '.join(data.get('hashtags',[])))
    scenes=[]
    for i,s in enumerate(data['scenes'],1):
        with st.expander(f'Scene {i}',expanded=i==1):
            n=st.text_area('Narration',s['narration'],key=f'n{i}')
            cap=st.text_input('On-screen caption',s['caption'],key=f'c{i}')
            vis=st.text_input('Visual cue',s['visual'],key=f'v{i}')
            scenes.append({'narration':n,'caption':cap,'visual':vis})
    st.header('5. Render video')
    gender=st.selectbox('Windows offline voice',['Default','Male','Female'])
    music_file=st.file_uploader('Optional music you have rights to use (MP3/WAV)',type=['mp3','wav'])
    st.warning('This creates a draft only. Nothing is uploaded or published.')
    if st.button('Render Shorts MP4',type='primary',use_container_width=True):
        try:
            audio=OUT/'voiceover.wav'
            with st.spinner('Generating offline narration...'): make_voice(' '.join(s['narration'] for s in scenes),audio,gender)
            music=None
            if music_file:
                music=OUT/f'background_music{Path(music_file.name).suffix.lower()}'; music.write_bytes(music_file.getbuffer())
            with st.spinner('Rendering vertical video with FFmpeg...'): vid,thumb=render({'scenes':scenes},audio,music)
            meta=OUT/'youtube_metadata.txt'; meta.write_text(f'TITLE\n{title}\n\nDESCRIPTION\n{desc}\n\nHASHTAGS\n{tags}\n',encoding='utf-8')
            st.session_state['video']=str(vid); st.session_state['thumb']=str(thumb); st.session_state['meta']=str(meta)
            st.success('Your draft is ready for review.')
        except Exception as ex: st.error(f'Rendering failed: {ex}')
if st.session_state.get('video') and Path(st.session_state['video']).exists():
    st.header('6. Preview and approve')
    st.video(st.session_state['video']); st.image(st.session_state['thumb'],width=220)
    p=Path(st.session_state['video']); st.download_button('Download MP4 draft',p.read_bytes(),file_name=p.name,mime='video/mp4',use_container_width=True)
    m=Path(st.session_state['meta']); st.download_button('Download title and description',m.read_text(encoding='utf-8'),file_name='youtube_metadata.txt')
    st.info('Publishing is intentionally manual. Inspect the video before uploading it to YouTube.')
st.caption('Local Ollama, Windows speech and FFmpeg rendering run on your PC. GPT, Claude and transcript retrieval require internet. This starter version uses designed title cards rather than AI-generated moving footage.')
