package nextflow.baitan

import groovy.transform.CompileStatic

/**
 * A promise phase as the wire carries it: the bare string `open`, or a one-key object
 * such as `{"settled": {...}}`. `of` flattens both to a map with a `phase` key.
 */
@CompileStatic
class Phase {

    static Map<String,Object> of(Object wire) {
        if( wire instanceof CharSequence )
            return [phase: wire.toString()] as Map<String,Object>
        final Map m = (Map) wire
        final key = m.keySet().first() as String
        final result = new LinkedHashMap<String,Object>((Map) m.get(key))
        result.phase = key
        return result
    }
}
