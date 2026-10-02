// Wrap an accepted ws connection; no server creation/listen occurs here.
// Authentication, origin checks, admission, and maximum unauthenticated peers belong
// to the future host upgrade handler. Bind one exact core allocation before calling.
export function bindWebSocket(gateway, streamId, role, ws) {
  let endpoint;
  const close = () => ws.terminate();
  try {
    endpoint = gateway.attach(streamId,role,{
      send(message) {
        if (ws.readyState !== 1 || ws.bufferedAmount > 65536) throw Error('Transport unavailable');
        ws.send(JSON.stringify(message), error => { if (error) endpoint?.close(); });
      },close
    });
  } catch { close(); throw Error('Session unavailable'); }
  ws.on('message',(data,binary) => {
    if (binary || data.length > 65536) { endpoint.close(); return; }
    try { endpoint.receive(data.toString('utf8')); } catch { close(); }
  });
  ws.on('error',() => endpoint.close());
  ws.on('close',() => endpoint.close());
  return endpoint;
}
