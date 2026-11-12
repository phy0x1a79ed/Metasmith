package nextflow.baitan

import spock.lang.Specification

/** Golden values computed by running baitan-proto's own `instance_id`, `offer_key` and `slot_id`. */
class IdsTest extends Specification {

    def 'hashes match baitan-proto'() {
        given:
        def a = Ids.instanceId([path: '/data/a.fa', origin: 'mizar'])
        def spec = [
            script : "echo \"hi\"\n\té ü\u0001",
            stage  : ['in.fa': [id: a, src: '/data/a.fa']],
            outputs: ['out.txt'],
        ]
        def b = Ids.offerKey('task', [hash: 'abc123', contract: 'nextflow-task'], [a], spec, null)
        def c = Ids.slotId(b, 'out')
        def place = Ids.offerKey('place', [:], [c], [path: '/w'], 'mizar')

        expect:
        a == '69157036cafdf7f8c81d26b379f92449'
        b == 'de5706fd7ba0cc46ff6fc5335cac21e4'
        c == '0b6662bbe9442f90e152e80a9c8ae536'
        place == '5452083602f162e22ca9b2e67896abdb'
    }
}
