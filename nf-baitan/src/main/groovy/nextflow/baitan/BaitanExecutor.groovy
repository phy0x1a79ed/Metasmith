package nextflow.baitan

import java.util.concurrent.CompletableFuture
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit

import groovy.transform.CompileStatic
import groovy.util.logging.Slf4j
import nextflow.executor.Executor
import nextflow.processor.TaskHandler
import nextflow.processor.TaskMonitor
import nextflow.processor.TaskPollingMonitor
import nextflow.processor.TaskRun
import nextflow.util.Duration
import nextflow.util.ServiceName
import org.pf4j.ExtensionPoint

/**
 * Routes each Nextflow task through baitan as one offer set. Config scope `baitan`:
 * `connect` (command bridging to the market, default `baitan connect`) and `place`
 * (the provider id of the machine that runs Nextflow).
 */
@Slf4j
@CompileStatic
@ServiceName('baitan')
class BaitanExecutor extends Executor implements ExtensionPoint {

    BaitanClient client
    String place

    /** Listeners by promise id, to route events. */
    final ConcurrentHashMap<String,Listener> handlers = new ConcurrentHashMap<>()
    /** Checker runs that may still owe a review. */
    final Set<CompletableFuture<Void>> checks = ConcurrentHashMap.newKeySet()
    /** Settled instance ids to dispose at the end, and the ones that stay. */
    final Set<String> intermediates = ConcurrentHashMap.newKeySet()
    final Set<String> finals = ConcurrentHashMap.newKeySet()

    @Override
    protected void register() {
        super.register()
        final cfg = (session.config.baitan ?: [:]) as Map
        place = cfg.place as String
        client = new BaitanClient((cfg.connect ?: 'baitan connect') as String)
        client.onEvent = { Map status -> onEvent(status) }
        client.onConnected = { onConnected() }
        client.start()
    }

    /** Watch every promise, and learn what happened to the open ones while the link was down. */
    private void onConnected() {
        client.ask('watch', [promises: []])
        for( Map.Entry<String,Listener> e : handlers.entrySet() ) {
            if( !e.value.isFinished() )
                client.ask('status', [promise: e.key]).thenAccept { Object r -> onEvent((Map) r) }
        }
    }

    private void onEvent(Map status) {
        final handler = handlers.get(status.promise as String)
        if( handler == null ) return
        handler.onPhase(Phase.of(status.phase))
        signal()
    }

    @Override
    protected TaskMonitor createTaskMonitor() {
        TaskPollingMonitor.create(session, config, name, 1000, Duration.of('1 sec'))
    }

    @Override
    TaskHandler createTaskHandler(TaskRun task) {
        new BaitanTaskHandler(task, this)
    }

    /** Wait for the owed reviews, dispose the intermediates of a successful run, then close the link. */
    @Override
    void shutdown() {
        try {
            CompletableFuture.allOf(checks as CompletableFuture[]).get(60, TimeUnit.SECONDS)
        }
        catch( Exception e ) {
            log.warn "[baitan] a checker did not finish: ${e.message}"
        }
        try {
            if( session.isSuccess() && intermediates ) {
                final ids = new ArrayList<String>(intermediates).sort()
                client.ask('dispose', [ids: ids]).get(30, TimeUnit.SECONDS)
                log.debug "[baitan] disposed ${ids.size()} intermediates"
            }
        }
        catch( Exception e ) {
            log.warn "[baitan] dispose failed: ${e.message}"
        }
        client?.close()
    }
}
