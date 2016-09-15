document.addEventListener "DOMContentLoaded", ->
  console.log "Coffeescript enabled"
  riot.mount 'x-boxes',
    name: 'intergated'
    items: [
      {title: 'Coffeescript', value:'js'},
      {title: 'RiotJS', value:'tag'}
    ]
