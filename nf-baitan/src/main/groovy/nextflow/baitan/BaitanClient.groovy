package nextflow.baitan

import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import java.util.function.Consumer

import groovy.transform.CompileStatic
import groovy.util.logging.Slf4j

/**
 * The caller's end of the baitan wire: one JSON envelope per line over the stdio of the
 * `baitan.connect` command. Each ask returns a future completed by the reply with the same
 * `replyTo`; `event` sends go to {@link #onEvent}. When the link drops, pending asks fail and
 * the client reconnects, then calls {@link #onConnected}.
 */
@Slf4j
@CompileStatic
class BaitanClient {

    static class Raised extends RuntimeException {
        final String name
        Raised(String name, String message) { super("$name: $message".toString()); this.name = name }
    }

    final String connect
    final String caller = 'nextflow-' + UUID.randomUUID().toString().substring(0, 8)
    Consumer<Map> onEvent = { Map e -> } as Consumer<Map>
    Runnable onConnected = { } as Runnable

    private final ConcurrentHashMap<String,CompletableFuture<Object>> pending = new ConcurrentHashMap<>()
    private volatile Process proc
    private volatile Writer out
    private volatile boolean closed

    BaitanClient(String connect) { this.connect = connect }

    void start() {
        open()
        onConnected.run()
    }

    private void open() {
        final p = new ProcessBuilder('bash', '-c', connect).redirectError(ProcessBuilder.Redirect.INHERIT).start()
        out = new BufferedWriter(new OutputStreamWriter(p.outputStream, 'UTF-8'))
        proc = p
        final reader = new BufferedReader(new InputStreamReader(p.inputStream, 'UTF-8'))
        Thread.start('baitan-reader') { read(reader) }
    }

    CompletableFuture<Object> ask(String selector, Map args) {
        final id = UUID.randomUUID().toString()
        final future = new CompletableFuture<Object>()
        pending.put(id, future)
        try {
            write(selector, args, id)
        }
        catch( IOException e ) {
            pending.remove(id)
            future.completeExceptionally(e)
        }
        return future
    }

    private synchronized void write(String selector, Map args, String id) {
        final w = out
        if( w == null ) throw new IOException('baitan link is down')
        final env = new LinkedHashMap<String,Object>()
        env.v = 1
        env.id = id
        env.from = caller
        env.to = 'market'
        env.selector = selector
        env.args = args
        w.write(Json.encode(env))
        w.write('\n')
        w.flush()
    }

    private void read(BufferedReader reader) {
        try {
            String line
            while( (line = reader.readLine()) != null ) {
                try { dispatch((Map) Json.parse(line)) }
                catch( Exception e ) { log.warn "[baitan] bad line: $line -- ${e.message}" }
            }
        }
        catch( IOException e ) {
            log.debug "[baitan] read failed: ${e.message}"
        }
        linkDown()
    }

    private void dispatch(Map env) {
        final selector = env.selector as String
        final args = env.args
        final replyTo = env.replyTo as String
        if( replyTo != null ) {
            final f = pending.remove(replyTo)
            if( f == null ) return
            switch( selector ) {
                case 'return': f.complete(args); break
                case 'raise': f.completeExceptionally(new Raised(((Map) args).name as String, ((Map) args).message as String)); break
                default: f.completeExceptionally(new Raised(selector, args?.toString() ?: ''))
            }
        }
        else if( selector == 'event' )
            onEvent.accept((Map) args)
        else
            log.debug "[baitan] ignored $selector"
    }

    private void linkDown() {
        out = null
        final failure = new IOException('baitan link closed')
        for( String id : new ArrayList<String>(pending.keySet()) )
            pending.remove(id)?.completeExceptionally(failure)
        if( closed ) return
        long wait = 1000
        for( int attempt = 0; attempt < 8 && !closed; attempt++ ) {
            log.warn "[baitan] link down; reconnecting in ${wait} ms"
            sleep(wait)
            try { open(); onConnected.run(); return }
            catch( Exception e ) { log.warn "[baitan] reconnect failed: ${e.message}"; wait = Math.min(wait * 2, 15000) }
        }
        log.error '[baitan] giving up on the link'
    }

    void close() {
        closed = true
        try { out?.close() } catch( IOException e ) { }
        final p = proc
        if( p != null && !p.waitFor(5, TimeUnit.SECONDS) )
            p.destroy()
    }
}
