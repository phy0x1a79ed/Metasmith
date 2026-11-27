// p01 pulls the image `env` names, and each sample's p02 reads `env` held
// until that pull is done -- in codegen's shape, including the launch's
// workflow.pulls.json saying whether the pull runs at all.
include { given; mock1 as p01; mock2 as p02 } from './mocks.nf'

workflow {
main:
o = new Orchestrator(Channel.fromList([null]))
_lf = new groovy.json.JsonSlurper().parseText(file("workflow.lineage_of_given.json").text)
l = _lf.lineage
o.seedParents(_lf.child2parent)
o.pulls(file("workflow.pulls.json"))
o.ch._env = (o.postIn([given("inputs/env", l)], ["env"]))[0]
o.ch._reads = (o.postIn([given("inputs/reads", l)], ["reads"]))[0]

k = ['pulled']
if (o.pulling(1)) { o.ch._pulled = (o.post(o.asStreams(p01(o.group('env', [o.ch._env], k, 1))), k, ['slot-pulled']))[0]; o.ch._env = o.after(o.ch._env, o.ch._pulled) } else { o.ch._pulled = o.skipped('pulled') }
k = ['out']
o.ch._out = (o.post(o.asStreams(p02(o.group('reads', [o.ch._reads, o.ch._env], k, 1))), k, ['slot-out']))[0]
o.publish(o.ch._pulled).subscribe { x -> println("PUBLISHED pulled") }
o.seal()
}
