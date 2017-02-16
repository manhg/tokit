<x-boxes>
    <label each={ item in opts.items }>
        <input type=checkbox name={ opts.name } onchange={ show } value={ item.value }>
        <span>{ item.title }</span>
    </label>
    <div>{ chosen }</div>
    <script type=coffee>
    @show = (e) =>
        @update {chosen: e.target.value}
    </script>
</x-boxes>
