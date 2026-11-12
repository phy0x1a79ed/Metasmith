package nextflow.baitan

import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.Paths
import java.util.concurrent.CompletableFuture

import groovy.transform.CompileStatic
import groovy.util.logging.Slf4j

/**
 * The checker of a settled task: offered as a task step on the checked output, its report placed back
 * here, its scores per declared axis sent as the review of the checked promise. It never fails the task.
 */
@Slf4j
@CompileStatic
class CheckRun implements Listener {

    private final BaitanExecutor executor
    private final String reviewed
    private final Declaration check
    private final List<Map> axes
    private final String outId
    private final String holder
    private final Path dir
    private volatile boolean finished
    final CompletableFuture<Void> done = new CompletableFuture<>()

    CheckRun(BaitanExecutor executor, String reviewed, Declaration decl, String outId, String holder, Path workDir) {
        this.executor = executor
        this.reviewed = reviewed
        this.check = decl.checker
        this.axes = decl.axes
        this.outId = outId
        this.holder = holder
        this.dir = workDir.resolve('.baitan-check')
    }

    boolean isFinished() { finished }

    void start() {
        if( !executor.place ) {
            log.warn "[baitan] checker for ${reviewed} skipped: 'baitan.place' is not set"
            return
        }
        executor.checks.add(done)
        executor.client.ask('offer', [set: buildSet()]).whenComplete { Object reply, Throwable err ->
            if( err != null ) {
                log.warn "[baitan] checker offer failed: ${err.message}"
                finish()
                return
            }
            executor.handlers.put(((Map) reply).promise as String, this)
        }
    }

    private Map<String,Object> buildSet() {
        final stage = new TreeMap<String,Object>()
        final inputs = new ArrayList<String>([outId])
        final start = new ArrayList<Map>([Fact.at(outId, holder)])
        stage.put(check.input, [id: outId] as Map<String,Object>)
        for( Map.Entry<String,Map<String,String>> e : check.givens.entrySet() ) {
            final id = Ids.instanceId(e.value)
            stage.put(Paths.get(e.key).fileName.toString(), [id: id, src: e.key] as Map<String,Object>)
            inputs.add(id)
            start.add(Fact.at(id, executor.place))
        }
        inputs.sort()
        final spec = new LinkedHashMap<String,Object>()
        spec.script = "set -ue\n${check.script}\n".toString()
        spec.stage = stage
        spec.outputs = [check.report]
        final task = [op: 'task', props: check.props, inputs: inputs, slots: ['out'], spec: spec] as Map<String,Object>
        final out = Ids.slotId(Ids.offerKey('task', check.props, inputs, spec, null), 'out')
        final place = [op: 'place', props: [:], inputs: [out], slots: [], spec: [path: dir.toString()], to: executor.place] as Map<String,Object>
        return [steps: [task, place], start: start] as Map<String,Object>
    }

    void onPhase(Map<String,Object> phase) {
        final p = phase.phase
        if( p == 'settled' )
            review()
        else if( p == 'failed' ) {
            log.warn "[baitan] checker for ${reviewed} failed: ${phase.name}: ${phase.message}"
            finish()
        }
    }

    private void review() {
        try {
            final scores = readScores()
            if( !scores ) {
                log.warn "[baitan] checker for ${reviewed} left no score for any axis"
                finish()
                return
            }
            executor.client.ask('review', [promise: reviewed, scores: scores]).whenComplete { Object r, Throwable err ->
                if( err != null ) log.warn "[baitan] review of ${reviewed} failed: ${err.message}"
                finish()
            }
        }
        catch( Exception e ) {
            log.warn "[baitan] review of ${reviewed} failed: ${e.message}"
            finish()
        }
    }

    /** The mean of each axis's column over the report's rows. */
    private Map<String,Double> readScores() {
        final lines = Files.readAllLines(dir.resolve(check.report)).findAll { it.trim() }
        final header = lines.first().split('\t', -1) as List<String>
        final scores = new LinkedHashMap<String,Double>()
        for( Map axis : axes ) {
            final col = header.indexOf((axis.column ?: axis.name) as String)
            final values = lines.tail().collect { it.split('\t', -1) }.findAll { it.length > col }.collect { it[col].trim() }.findAll { it }
            if( col >= 0 && values )
                scores.put(axis.name as String, (double) (values.collect { Double.parseDouble(it) }.sum() as double) / values.size())
        }
        return scores
    }

    private void finish() {
        finished = true
        done.complete(null)
    }
}
