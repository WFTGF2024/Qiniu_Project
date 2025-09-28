/**
 * Lightweight WAV recorder using ScriptProcessorNode.
 * Produces mono 16kHz 16-bit PCM WAV Blob.
 */
export class WavRecorder {
  constructor({ targetSampleRate = 16000 } = {}){
    this.targetSampleRate = targetSampleRate
    this._chunks = []
    this._recording = false
  }

  async start(){
    this.stream = await navigator.mediaDevices.getUserMedia({ audio:true })
    this.audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    this.source = this.audioCtx.createMediaStreamSource(this.stream)
    const bufferSize = 4096
    this.processor = this.audioCtx.createScriptProcessor(bufferSize, 1, 1)
    this.source.connect(this.processor)
    this.processor.connect(this.audioCtx.destination)
    this._recording = true
    this._inputData = []
    this.processor.onaudioprocess = (e)=>{
      if(!this._recording) return
      const input = e.inputBuffer.getChannelData(0)
      // copy
      this._inputData.push(new Float32Array(input))
    }
  }

  async stop(){
    this._recording = false
    if(this.processor){ this.processor.disconnect() }
    if(this.source){ this.source.disconnect() }
    if(this.audioCtx){ await this.audioCtx.close() }
    if(this.stream){
      this.stream.getTracks().forEach(t=>t.stop())
    }
    const data = this._mergeBuffers(this._inputData)
    const down = this._downsample(data, this.audioCtx.sampleRate, this.targetSampleRate)
    const wav = this._encodeWAV(down, this.targetSampleRate)
    return new Blob([wav], { type:'audio/wav' })
  }

  _mergeBuffers(bufs){
    let len = 0
    for(const b of bufs) len += b.length
    const res = new Float32Array(len)
    let off = 0
    for(const b of bufs){
      res.set(b, off); off += b.length
    }
    return res
  }

  _downsample(buffer, srIn, srOut){
    if(srOut === srIn) return buffer
    const ratio = srIn / srOut
    const outLen = Math.round(buffer.length / ratio)
    const out = new Float32Array(outLen)
    let offset = 0
    for(let i=0;i<outLen;i++){
      const nextOffset = Math.round((i+1)*ratio)
      let sum = 0, count = 0
      for(let j=offset; j<nextOffset && j<buffer.length; j++){
        sum += buffer[j]; count++
      }
      out[i] = sum / (count || 1)
      offset = nextOffset
    }
    return out
  }

  _encodeWAV(samples, sampleRate){
    const bytesPerSample = 2
    const blockAlign = bytesPerSample * 1
    const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample)
    const view = new DataView(buffer)

    // RIFF header
    this._writeString(view, 0, 'RIFF')
    view.setUint32(4, 36 + samples.length * bytesPerSample, true)
    this._writeString(view, 8, 'WAVE')

    // fmt chunk
    this._writeString(view, 12, 'fmt ')
    view.setUint32(16, 16, true) // PCM
    view.setUint16(20, 1, true)  // PCM
    view.setUint16(22, 1, true)  // mono
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, sampleRate * blockAlign, true)
    view.setUint16(32, blockAlign, true)
    view.setUint16(34, 8 * bytesPerSample, true)

    // data
    this._writeString(view, 36, 'data')
    view.setUint32(40, samples.length * bytesPerSample, true)

    // PCM 16-bit
    let offset = 44
    for(let i=0;i<samples.length;i++){
      let s = Math.max(-1, Math.min(1, samples[i]))
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
      offset += 2
    }
    return view
  }

  _writeString(view, offset, str){
    for(let i=0;i<str.length;i++){
      view.setUint8(offset+i, str.charCodeAt(i))
    }
  }
}