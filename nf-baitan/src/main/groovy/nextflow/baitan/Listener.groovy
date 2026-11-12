package nextflow.baitan

import groovy.transform.CompileStatic

/** Whatever follows one promise through its phases. */
@CompileStatic
interface Listener {
    boolean isFinished()
    void onPhase(Map<String,Object> phase)
}
