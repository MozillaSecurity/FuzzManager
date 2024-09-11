function HashParamManager() {
  let instance = this
  instance.state = {}
  instance.query = null

  instance.update_state = function() {
    instance.query = null
    window.location.hash.substr(1).split('&').forEach(function(s) {
      let kv = s.split("=")

      if (kv.length >= 2) {
        let k = kv.shift()
        let v = kv.join("=")
        instance.state[k] = v
      }
    })
  }

  instance.update_hash = function() {
    let query = instance.get_query()
    window.location.hash = query
  }

  instance.get_value = function(k, dv) {
    if (k in instance.state)
      return instance.state[k]
    return dv
  }

  instance.get_query = function() {
    if (instance.query == null)  {
      instance.query = Object.keys(instance.state).map(function(k) {
        return k + "=" + instance.state[k]
      }).join("&")
    }

    return instance.query
  }

  instance.update_value = function(k,v) {
    instance.query = null
    if (v != "") {
      instance.state[k] = v
    } else {
      delete instance.state[k]
    }
  }

  instance.forEach = function(f) {
    Object.keys(instance.state).forEach(function(k) {
      f(k, instance.state[k])
    })
  }

  // Update our state once initially
  instance.update_state()
}
