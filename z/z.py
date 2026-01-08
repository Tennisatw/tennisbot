from faster_whisper import WhisperModel
m=WhisperModel('small', device='cuda', compute_type='float16')
segs,_=m.transcribe(r"C:/Users/wqw/Desktop/0.wav")
print(' '.join([s.text for s in segs]))