
import org.apache.beam.sdk.Pipeline;
import org.apache.beam.sdk.io.TextIO;
import org.apache.beam.sdk.options.PipelineOptions;
import org.apache.beam.sdk.options.PipelineOptionsFactory;
//what transforms do I need?
//Examples from tutorial
//import org.apache.beam.sdk.transforms.Count;
//import org.apache.beam.sdk.transforms.DoFn;
//tutorial imports sdk.values.KV; also from Apache Beam to write output

public class FitData {
	public static void main(String[] args){
		//create PipelineOptions object
		PipelineOptions options = PipelineOptionsFactory.create();
		//Create the Pipeline object with the options we defined above
		Pipeline p = Pipeline.create(options);

		//Apply the pipeline's transforms. 

		@TODO
		p.apply(TextIO.read().from("[BUCKET NAME]"))
		//add more transformations by using .apply()
		//combine member data (ID, name, gender, age, height, weight) and fitness app data (Calories consumed, calories burned, hours slept) by date
	}
}