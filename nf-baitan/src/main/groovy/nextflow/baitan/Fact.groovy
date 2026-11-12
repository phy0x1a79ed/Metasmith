package nextflow.baitan

import groovy.transform.CompileStatic

/** The knowledge triple `(id, at, provider)` of the offer set's starting state. */
@CompileStatic
class Fact {
    static Map at(String id, String provider) {
        return [s: [id: id], p: [rel: 'at'], o: [provider: provider]]
    }
}
