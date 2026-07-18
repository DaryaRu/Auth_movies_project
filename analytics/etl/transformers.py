from schemas import EventMessage, MovieViewRow


class EventTransformer:
    @staticmethod
    def transform(event: EventMessage) -> MovieViewRow:
        if event.object_id is None:
            raise ValueError("Не передано значение object_id")
        payload = event.payload
        
        if not (viewed_frame := payload.get("viewed_frame")):
            raise ValueError("Не передано значение viewed_frame в payload")
        
        if not (movie_duration := payload.get("movie_duration")):
            raise ValueError("Не передано значение movie_duration в payload")

        return MovieViewRow(
            user_id=event.user_id,
            movie_id=event.object_id,
            viewed_frame=viewed_frame,
            movie_duration=movie_duration,
            event_time=event.event_time,
        )
