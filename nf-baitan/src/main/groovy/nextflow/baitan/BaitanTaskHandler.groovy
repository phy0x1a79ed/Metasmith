package nextflow.baitan

import java.nio.file.Files
import java.nio.file.Path

import groovy.transform.CompileStatic
import groovy.util.logging.Slf4j
import nextflow.processor.TaskHandler
import nextflow.processor.TaskRun
import nextflow.processor.TaskStatus

/**
 * One Nextflow task as one baitan offer set: a `task` step, plus a `place` step back to the
 * requester when the task publishes. The work dir ends up holding stubs and a manifest only.
 */
@Slf4j
@CompileStatic
class BaitanTaskHandler extends TaskHandler implements Listener {

    static final String MANIFEST = '.baitan-manifest.json'

    private final BaitanExecutor executor
    private final Path workDir
    private String slotOut
    private Declaration decl
    private boolean publishes
    private volatile String promise
    private volatile boolean killRequested
    /** Latest phase from events and replies, flattened by {@link Phase#of}. */
    volatile Map<String,Object> phase

    BaitanTaskHandler(TaskRun task, BaitanExecutor executor) {
        super(task)
        this.executor = executor
        this.workDir = task.workDir
    }

    void onPhase(Map<String,Object> p) { phase = p }

    boolean isFinished() {
        final p = phase?.phase
        return p == 'settled' || p == 'failed'
    }

    @Override
    void submit() {
        final set = buildSet()
        status = TaskStatus.SUBMITTED
        executor.client.ask('offer', [set: set]).whenComplete { Object reply, Throwable err ->
            if( err != null ) {
                final name = err instanceof BaitanClient.Raised ? ((BaitanClient.Raised) err).name : 'LinkError'
                phase = [phase: 'failed', name: name, message: err.message] as Map<String,Object>
                executor.signal()
                return
            }
            promise = ((Map) reply).promise as String
            executor.handlers.put(promise, this)
            if( killRequested )
                executor.client.ask('cancel', [promise: promise])
        }
    }

    private String placedPath() {
        return executor.placeRoot ? "${executor.placeRoot}/${workDir.parent.fileName}/${workDir.fileName}".toString() : workDir.toString()
    }

    private Declaration declaration() {
        final ext = task.config.get('ext')
        return Declaration.of(ext instanceof Map ? ((Map) ext).get('baitan') : null)
    }

    private Map<String,Object> buildSet() {
        final place = executor.place
        decl = declaration()
        final stage = new TreeMap<String,Object>()
        final start = new LinkedHashMap<String,Map>()
        for( Map.Entry<String,Path> e : task.getInputFilesMap().entrySet() ) {
            final ref = inputRef(e.value, place, decl)
            final id = ref.stage.get('id') as String
            stage.put(e.key, ref.stage)
            start.put(id, Fact.at(id, ref.provider))
        }
        final inputs = new ArrayList<String>(start.keySet()).sort()
        final outputs = new ArrayList<String>(task.getOutputFilesNames() as Collection<String>).unique().sort()
        final script = launchScript()

        final spec = new LinkedHashMap<String,Object>()
        spec.script = script
        spec.stage = stage
        spec.outputs = outputs
        final Map<String,String> props = decl != null ? decl.props : [contract: 'nextflow-task', hash: task.hash.toString()] as Map<String,String>
        final step = new LinkedHashMap<String,Object>()
        step.op = 'task'
        step.props = new TreeMap<String,String>(props)
        step.inputs = inputs
        step.slots = ['out']
        step.spec = spec
        final List<Map<String,Object>> steps = [step]

        slotOut = Ids.slotId(Ids.offerKey('task', props, inputs, spec, null), 'out')
        publishes = !task.config.getPublishDir().isEmpty()
        if( publishes ) {
            if( !place ) throw new IllegalStateException("A process publishes but 'baitan.place' is not set")
            steps.add([op: 'place', props: [:], inputs: [slotOut], slots: [], spec: [path: placedPath()], to: place] as Map<String,Object>)
        }

        final memMb = task.config.getMemory()?.toMega() ?: 2048L
        final set = new LinkedHashMap<String,Object>()
        set.steps = steps
        set.start = new ArrayList(start.values())
        if( executor.runAt ) set.place = executor.runAt
        set.resources = [cpus: task.config.getCpus(), mem_mb: memMb] as Map<String,Object>
        if( decl?.axes ) {
            final axes = new ArrayList<Map<String,Object>>()
            axes.add([name: 'time', weight: 1.0d, higher_better: false] as Map<String,Object>)
            for( Map a : decl.axes )
                axes.add([name: a.name, weight: a.weight ?: 0.0d, higher_better: a.higher_better ?: false] as Map<String,Object>)
            set.axes = axes
        }
        return set
    }

    /** The task script as a body the provider can run without Nextflow's wrapper. */
    private String launchScript() {
        final body = task.getScript()
        final sb = new StringBuilder('set -ue\n')
        for( Map.Entry<String,String> e : task.getEnvironment().entrySet() )
            sb.append("export ${e.key}='${e.value.replace("'", "'\\''")}'\n")
        final first = body.readLines().find() ?: ''
        if( first.startsWith('#!') && !(first =~ /\b(ba|da)?sh\b/) )
            sb.append("cat > .baitan-task <<'BAITAN_EOF'\n${body}\nBAITAN_EOF\nchmod +x .baitan-task\n./.baitan-task\n")
        else
            sb.append(body).append('\n')
        final script = sb.toString()
        Files.writeString(workDir.resolve('.command.sh'), script)
        return script
    }

    /**
     * Where an input comes from: a stub under an upstream manifest, or a leaf file held by the
     * requester's place, named by its declared property set when the process declares one.
     * Returns the stage entry and the provider that holds the instance.
     */
    private InputRef inputRef(Path file, String place, Declaration decl) {
        for( Path dir = file.parent; dir != null && file.fileSystem == java.nio.file.FileSystems.getDefault(); dir = dir.parent ) {
            final manifest = dir.resolve(MANIFEST)
            if( !Files.exists(manifest) ) continue
            final m = (Map) Json.parse(Files.readString(manifest))
            final id = (m.ids as Map).out as String
            final stage = [id: id, path: dir.relativize(file).toString()] as Map<String,Object>
            return new InputRef(stage, (m.providers as Map)[id] as String)
        }
        if( !place ) throw new IllegalStateException("A process reads a file but 'baitan.place' is not set")
        final path = file.fileSystem == java.nio.file.FileSystems.getDefault() ? file.toAbsolutePath().toString() : file.toUriString()
        final id = decl?.givenId(path) ?: Ids.instanceId([path: path, origin: place] as Map<String,String>)
        return new InputRef([id: id, src: path] as Map<String,Object>, place)
    }

    private static class InputRef {
        final Map<String,Object> stage
        final String provider
        InputRef(Map<String,Object> stage, String provider) { this.stage = stage; this.provider = provider }
    }

    @Override
    boolean checkIfRunning() {
        if( status == TaskStatus.SUBMITTED && phase != null && phase.phase != 'open' ) {
            status = TaskStatus.RUNNING
            return true
        }
        return false
    }

    @Override
    boolean checkIfCompleted() {
        if( !isFinished() )
            return false
        final err = workDir.resolve('.command.err')
        if( phase.phase == 'settled' ) {
            try {
                writeStubs()
                task.exitStatus = 0
            }
            catch( Exception e ) {
                Files.writeString(err, e.message ?: e.toString())
                task.exitStatus = 1
            }
        }
        else {
            Files.writeString(err, "${phase.name}: ${phase.message}".toString())
            task.exitStatus = 1
        }
        Files.writeString(workDir.resolve('.exitcode'), "${task.exitStatus}\n".toString())
        for( String f : ['.command.out', '.command.log'] )
            Files.writeString(workDir.resolve(f), '')
        if( !Files.exists(err) ) Files.writeString(err, '')
        task.stdout = workDir.resolve('.command.out')
        task.stderr = err
        status = TaskStatus.COMPLETED
        return true
    }

    /** Stub files for the `out` listing, and the manifest. A real file already placed here stays. */
    private void writeStubs() {
        final provider = phase.provider as String
        final listing = (phase.listing ?: [:]) as Map<String,List<String>>
        String outId = listing.containsKey(slotOut) ? slotOut : (listing.size() == 1 ? listing.keySet().first() : null)
        if( outId == null )
            throw new IllegalStateException("settle has no listing for the task's out slot ${slotOut}")
        for( String rel : listing.get(outId) ) {
            final stub = workDir.resolve(rel)
            if( Files.exists(stub) ) continue
            Files.createDirectories(stub.parent)
            Files.writeString(stub, Json.encode([id: outId, path: rel, provider: provider]))
        }
        final manifest = [promise: promise, ids: [out: outId], providers: [(outId): provider]]
        Files.writeString(workDir.resolve(MANIFEST), Json.encode(manifest))
        (publishes ? executor.finals : executor.intermediates).add(outId)
        if( decl?.checker != null ) {
            try {
                new CheckRun(executor, promise, decl, outId, provider, workDir).start()
            }
            catch( Exception e ) {
                log.warn "[baitan] checker for ${promise} not started: ${e.message}"
            }
        }
    }

    @Override
    protected void killTask() {
        killRequested = true
        if( promise != null )
            executor.client.ask('cancel', [promise: promise])
    }
}
